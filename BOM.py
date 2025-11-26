import csv
import math
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
from io import BytesIO
from pdf2image import convert_from_path

# ============================================================
# Component Box Class
# ============================================================

class ComponentBox:
    """A rectangular component drawn on the canvas with rotation + values."""

    def __init__(self, canvas, ref, x, y, angle, comp_type="Unknown", value="", unit=""):
        self.canvas = canvas
        self.ref = ref
        self.x = x
        self.y = y
        self.angle = float(angle)

        # Auto-detect type + default units
        first = ref[0].upper()
        if first == "C":
            self.comp_type = "Capacitor"
            self.unit = unit if unit else "nF"
        elif first == "R":
            self.comp_type = "Resistor"
            self.unit = unit if unit else "Ohms"
        elif first == "L":
            self.comp_type = "Inductor"
            self.unit = unit if unit else "nH"
        else:
            self.comp_type = comp_type
            self.unit = unit if unit else ""

        self.value = value

        self.width = 60
        self.height = 20

        self.rect = None
        self.label = None

        self.draw()
        self.bind_events()

    # ---------------------------------------------------------
    # Label formatting
    # ---------------------------------------------------------
    def formatted_label(self):
        if self.value and self.unit:
            return f"{self.ref} {self.value}{self.unit}"
        return self.ref

    # ---------------------------------------------------------
    # Drawing component
    # ---------------------------------------------------------
    def draw(self):
        w = self.width / 2
        h = self.height / 2

        # Rectangle before rotation
        corners = [
            (-w, -h),
            ( w, -h),
            ( w,  h),
            (-w,  h)
        ]

        theta = math.radians(self.angle)
        rotated = []

        for (cx, cy) in corners:
            rx = cx * math.cos(theta) - cy * math.sin(theta)
            ry = cx * math.sin(theta) + cy * math.cos(theta)
            rotated.append((self.x + rx, self.y + ry))

        points = [p for xy in rotated for p in xy]

        self.rect = self.canvas.create_polygon(
            points,
            fill="lightblue",
            outline="black",
            width=2
        )

        # Smart label placement
        angle = self.angle % 360
        offset = 6
        side_offset = 12

        if 315 <= angle or angle < 45:
            lx, ly = self.x, self.y + h + offset
        elif 45 <= angle < 135:
            lx, ly = self.x, self.y + 30 + offset
        elif 135 <= angle < 225:
            lx, ly = self.x, self.y + h + offset
        else:
            lx, ly = self.x, self.y + 30 + offset

        self.label = self.canvas.create_text(
            lx, ly,
            text=self.formatted_label(),
            font=("Arial", 9)
        )

    # ---------------------------------------------------------
    # Right-click pop-up editor
    # ---------------------------------------------------------
    def bind_events(self):
        for tag in (self.rect, self.label):
            self.canvas.tag_bind(tag, "<Button-3>", self.right_click)

    def right_click(self, event):
        popup = tk.Toplevel()
        popup.title(f"Edit {self.ref}")

        tk.Label(popup, text=f"Reference: {self.ref}", font=("Arial", 12)).pack(pady=5)

        tk.Label(popup, text="Component Type:").pack()
        type_box = ttk.Combobox(
            popup,
            values=["Resistor", "Capacitor", "Inductor", "Unknown"]
        )
        type_box.set(self.comp_type)
        type_box.pack(pady=5)

        tk.Label(popup, text="Value (numeric):").pack()
        value_entry = tk.Entry(popup)
        value_entry.insert(0, self.value)
        value_entry.pack(pady=5)

        tk.Label(popup, text="Units:").pack()
        unit_box = ttk.Combobox(
            popup,
            values=["pF", "nF", "uF", "pH", "nH", "Ohms"]
        )
        unit_box.set(self.unit)
        unit_box.pack(pady=5)

        tk.Label(popup, text="Rotation Angle (deg):").pack()
        angle_entry = tk.Entry(popup)
        angle_entry.insert(0, str(self.angle))
        angle_entry.pack(pady=5)

        def save_changes():
            self.comp_type = type_box.get()
            self.value = value_entry.get()
            self.unit = unit_box.get()
            self.angle = float(angle_entry.get())

            self.canvas.delete(self.rect)
            self.canvas.delete(self.label)
            self.draw()
            self.bind_events()

            popup.destroy()

        tk.Button(popup, text="Save Changes", command=save_changes).pack(pady=10)

# ============================================================
# Layout Application
# ============================================================

class LayoutApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Chipset Layout Editor")

        self.components = []
        self.file_a = {}
        self.file_b = {}
        self.view_mode = "A"

        self.underlay_img = None
        self.underlay_canvas_img = None
        self.underlay_scale = 1.0
        self.underlay_offset_x = 0
        self.underlay_offset_y = 0
        self.underlay_opacity = 1.0

        self.layout_scale = 1.0  # NEW for spreading components

        # ============================================================
        # TOP BUTTON BAR
        # ============================================================
        top = tk.Frame(root)
        top.pack(fill="x", pady=5)

        tk.Button(top, text="Load File A", command=self.load_file_a).pack(side="left", padx=10)
        tk.Button(top, text="Load File B", command=self.load_file_b).pack(side="left", padx=10)
        tk.Button(top, text="Save File A", command=self.save_file_a).pack(side="left", padx=10)
        tk.Button(top, text="Save File B", command=self.save_file_b).pack(side="left", padx=10)

        tk.Button(top, text="Toggle A/B", command=self.toggle_view).pack(side="left", padx=10)
        tk.Button(top, text="Show Differences", command=self.show_differences).pack(side="left", padx=10)
        tk.Button(top, text="Load PDF Underlay", command=self.load_pdf_underlay).pack(side="left", padx=10)
        tk.Button(top, text="Clear", command=self.clear_canvas).pack(side="left", padx=10)

        # ============================================================
        # LEFT SIDEBAR
        # ============================================================
        sidebar = tk.Frame(root, width=260, bg="#e5e5e5")
        sidebar.pack(side="left", fill="y")

        tk.Label(sidebar, text="PDF Controls", bg="#e5e5e5", font=("Arial", 12, "bold")).pack(pady=5)

        tk.Label(sidebar, text="Scale").pack()
        self.scale_slider = tk.Scale(
            sidebar, from_=0.1, to=4.0, resolution=0.05,
            orient="horizontal",
            command=lambda v: self.update_underlay()
        )
        self.scale_slider.set(1.0)
        self.scale_slider.pack(fill="x")

        tk.Label(sidebar, text="Offset X").pack()
        self.offset_x_slider = tk.Scale(
            sidebar, from_=-1000, to=1000, resolution=1,
            orient="horizontal",
            command=lambda v: self.update_underlay()
        )
        self.offset_x_slider.set(0)
        self.offset_x_slider.pack(fill="x")

        tk.Label(sidebar, text="Offset Y").pack()
        self.offset_y_slider = tk.Scale(
            sidebar, from_=-1000, to=1000, resolution=1,
            orient="horizontal",
            command=lambda v: self.update_underlay()
        )
        self.offset_y_slider.set(0)
        self.offset_y_slider.pack(fill="x")

        tk.Label(sidebar, text="Opacity").pack()
        self.opacity_slider = tk.Scale(
            sidebar, from_=0.1, to=1.0, resolution=0.05,
            orient="horizontal",
            command=lambda v: self.update_underlay()
        )
        self.opacity_slider.set(1.0)
        self.opacity_slider.pack(fill="x")

        # ============================================================
        # NEW LAYOUT SCALE SLIDER
        # ============================================================
        tk.Label(sidebar, text="Layout Scale", bg="#e5e5e5", font=("Arial", 12, "bold")).pack(pady=(15,0))

        self.layout_scale_slider = tk.Scale(
            sidebar,
            from_=0.5,
            to=10.0,
            resolution=0.1,
            orient="horizontal",
            command=lambda v: self.on_layout_scale_changed()
        )
        self.layout_scale_slider.set(1.0)
        self.layout_scale_slider.pack(fill="x", padx=5, pady=5)

        # ============================================================
        # MAIN CANVAS
        # ============================================================
        self.canvas = tk.Canvas(root, width=1400, height=900, bg="white")
        self.canvas.pack(fill="both", expand=True)

    # ============================================================
    # CALLBACK: LAYOUT SCALE
    # ============================================================
    def on_layout_scale_changed(self):
        self.layout_scale = float(self.layout_scale_slider.get())
        self.redraw()

    # ============================================================
    # CLEAR CANVAS
    # ============================================================
    def clear_canvas(self):
        self.canvas.delete("all")
        self.components = []

    # ============================================================
    # PARSE CSV (safe loader)
    # ============================================================
    def parse_csv(self, filepath):
        data = {}
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ref = row.get("ReferenceID") or row.get("Reference") or row.get("Ref") or ""
                    if not ref:
                        continue

                    try:
                        x = float(row.get("X", ""))
                        y = float(row.get("Y", ""))
                    except:
                        continue

                    try:
                        angle = float(row.get("Angle", "0"))
                    except:
                        angle = 0

                    data[ref] = {
                        "x": x,
                        "y": y,
                        "angle": angle,
                        "value": row.get("Value", ""),
                        "unit": row.get("Unit", ""),
                        "comp_type": self.detect_type(ref),
                    }
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return {}

        return data

    # ============================================================
    # TYPE DETECTION BASED ON REFERENCE PREFIX
    # ============================================================
    def detect_type(self, ref):
        if not ref:
            return "Unknown"
        first = ref[0].upper()
        if first == "C":
            return "Capacitor"
        if first == "R":
            return "Resistor"
        if first == "L":
            return "Inductor"
        return "Unknown"

    # ============================================================
    # FILE A LOADER (CSV + XLSX MERGE)
    # ============================================================
    def load_file_a(self):
        # 1) Load XY CSV
        fp_csv = filedialog.askopenfilename(
            title="Select File A XY CSV",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not fp_csv:
            return

        file_a_xy = self.parse_csv(fp_csv)
        if not file_a_xy:
            messagebox.showerror("Error", "Invalid XY CSV.")
            return

        # 2) Load XLSX BOM
        fp_xlsx = filedialog.askopenfilename(
            title="Select BOM XLSX",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not fp_xlsx:
            messagebox.showerror("Error", "BOM XLSX required.")
            return

        bom_data = self.load_bom_xlsx(fp_xlsx)

        # 3) Merge BOM into XY
        for ref, info in file_a_xy.items():
            if ref in bom_data:
                raw_value = bom_data[ref]
                numeric, unit = self.parse_engineering_value(raw_value, info["comp_type"])
                if numeric is not None:
                    info["value"] = numeric
                if unit:
                    info["unit"] = unit

        # Save
        self.file_a = file_a_xy
        self.view_mode = "A"
        self.redraw()

        messagebox.showinfo("Loaded", "File A loaded with XY + BOM successfully.")

    # ============================================================
    # LOAD FILE B (CSV ONLY)
    # ============================================================
    def load_file_b(self):
        fp = filedialog.askopenfilename(
            title="Select File B CSV",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not fp:
            return
        self.file_b = self.parse_csv(fp)
        self.view_mode = "B"
        self.redraw()

    # ============================================================
    # SAVE FILE A
    # ============================================================
    def save_file_a(self):
        if not self.file_a:
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Save File A"
        )
        if not save_path:
            return

        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ReferenceID", "X", "Y", "Angle", "Value", "Unit"])
            for ref, v in self.file_a.items():
                writer.writerow([
                    ref,
                    round(v["x"], 4),
                    round(v["y"], 4),
                    v["angle"],
                    v["value"],
                    v["unit"]
                ])

        print("File A saved:", save_path)

    # ============================================================
    # SAVE FILE B
    # ============================================================
    def save_file_b(self):
        if not self.file_b:
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Save File B"
        )
        if not save_path:
            return

        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ReferenceID", "X", "Y", "Angle", "Value", "Unit"])
            for ref, v in self.file_b.items():
                writer.writerow([
                    ref,
                    round(v["x"], 4),
                    round(v["y"], 4),
                    v["angle"],
                    v["value"],
                    v["unit"]
                ])

        print("File B saved:", save_path)

    # ============================================================
    # XLSX BOM LOADER (Auto detect header)
    # ============================================================
    def load_bom_xlsx(self, filepath):
        from openpyxl import load_workbook

        wb = load_workbook(filepath, data_only=True)
        sheet = wb.active

        header_row = None
        col_ref = None
        col_val = None

        # Scan first 20 rows for header
        for r in range(1, 21):
            row_values = []
            for c in range(1, sheet.max_column + 1):
                cell = sheet.cell(row=r, column=c).value
                if cell:
                    row_values.append((c, str(cell).strip().lower()))

            columns = {text: col for col, text in row_values}

            if "reference designator" in columns and "value" in columns:
                header_row = r
                col_ref = columns["reference designator"]
                col_val = columns["value"]
                break

        if header_row is None:
            messagebox.showerror("Error", "Could not find header row with Reference Designator + Value")
            return {}

        # Parse below header
        bom = {}
        for r in range(header_row + 1, sheet.max_row + 1):
            ref_cell = sheet.cell(row=r, column=col_ref).value
            val_cell = sheet.cell(row=r, column=col_val).value

            if not ref_cell or not val_cell:
                continue

            ref_list_raw = str(ref_cell).strip()
            val = str(val_cell).strip()

            # Split multi-part references: commas, spaces, slashes
            refs = (
                ref_list_raw
                .replace(";", ",")
                .replace("/", ",")
                .replace(" ", ",")
                .split(",")
            )

            for ref in refs:
                ref = ref.strip()
                if ref:
                    bom[ref] = val


        return bom

    # ============================================================
    # ENGINEERING VALUE PARSER
    # ============================================================
    def parse_engineering_value(self, raw, comp_type):
        if not raw:
            return None, None

        raw = str(raw).strip().replace(" ", "").lower()

        if comp_type == "Capacitor":
            if raw.endswith("pf"):
                return float(raw[:-2]), "pF"
            if raw.endswith("nf"):
                return float(raw[:-2]), "nF"
            if raw.endswith("uf"):
                return float(raw[:-2]), "uF"
            if raw.replace(".", "").isdigit():
                return float(raw), "nF"
            return None, None

        if comp_type == "Resistor":
            if "k" in raw:
                return float(raw.replace("k", "")) * 1000, "Ohms"
            if "r" in raw:
                return float(raw.replace("r", "")), "Ohms"
            if raw.replace(".", "").isdigit():
                return float(raw), "Ohms"
            return None, None

        if comp_type == "Inductor":
            if raw.endswith("nh"):
                return float(raw[:-2]), "nH"
            if raw.endswith("uh"):
                return float(raw[:-2]), "uH"
            if raw.replace(".", "").isdigit():
                return float(raw), "nH"
            return None, None

        return None, None

    # ============================================================
    # TOGGLE VIEW
    # ============================================================
    def toggle_view(self):
        self.view_mode = "B" if self.view_mode == "A" else "A"
        self.redraw()

    # ============================================================
    # REDRAW LAYOUT (with layout_scale)
    # ============================================================
    def redraw(self):
        self.canvas.delete("all")

        data = self.file_a if self.view_mode == "A" else self.file_b
        if not data:
            return

        xs = [v["x"] for v in data.values()]
        ys = [v["y"] for v in data.values()]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        w = max_x - min_x
        h = max_y - min_y

        # Prevent tiny layouts → smush fix
        min_layout_size = 50
        if w < min_layout_size:
            w = min_layout_size
        if h < min_layout_size:
            h = min_layout_size

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        sx = (cw - 200) / w
        sy = (ch - 200) / h
        scale = min(sx, sy)

        padding = 100

        for ref, info in data.items():
            x = (info["x"] - min_x) * scale * self.layout_scale + padding
            y = (info["y"] - min_y) * scale * self.layout_scale + padding

            comp = ComponentBox(
                self.canvas, ref, x, y, info["angle"],
                comp_type=info["comp_type"],
                value=info["value"],
                unit=info["unit"]
            )
            self.components.append(comp)

        # Draw underlay on top
        self.update_underlay()

    # ============================================================
    # SHOW DIFFERENCES
    # ============================================================
    def show_differences(self):
        if not self.file_a or not self.file_b:
            messagebox.showerror("Error", "Load File A and File B first.")
            return

        diff_window = tk.Toplevel()
        diff_window.title("Differences")

        tree = ttk.Treeview(diff_window, columns=("oldV", "newV", "oldU", "newU"), show="headings")
        tree.pack(fill="both", expand=True)

        tree.heading("oldV", text="Old Value")
        tree.heading("newV", text="New Value")
        tree.heading("oldU", text="Old Unit")
        tree.heading("newU", text="New Unit")

        for ref in self.file_a:
            if ref not in self.file_b:
                continue

            a = self.file_a[ref]
            b = self.file_b[ref]

            if a["value"] != b["value"] or a["unit"] != b["unit"]:
                tree.insert("", "end", values=(a["value"], b["value"], a["unit"], b["unit"]))

    # ============================================================
    # PDF UNDERLAY
    # ============================================================
    def load_pdf_underlay(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not path:
            return

        try:
            images = convert_from_path(path, dpi=200, first_page=1, last_page=1)
            img = images[0]
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.underlay_img_original = img.convert("RGBA")
        self.update_underlay()

    def update_underlay(self):
        self.canvas.delete("UNDERLAY")

        if not hasattr(self, "underlay_img_original"):
            return

        scale = self.scale_slider.get()
        ox = self.offset_x_slider.get()
        oy = self.offset_y_slider.get()
        op = self.opacity_slider.get()

        img = self.underlay_img_original.resize(
            (int(self.underlay_img_original.width * scale),
             int(self.underlay_img_original.height * scale)),
            Image.LANCZOS
        )

        alpha = img.split()[3]
        alpha = alpha.point(lambda p: int(p * op))
        img.putalpha(alpha)

        self.underlay_img = ImageTk.PhotoImage(img)

        self.canvas.create_image(
            ox, oy,
            image=self.underlay_img,
            anchor="nw",
            tags="UNDERLAY"
        )

# ============================================================
# RUN APP
# ============================================================
root = tk.Tk()
app = LayoutApp(root)
root.mainloop()
