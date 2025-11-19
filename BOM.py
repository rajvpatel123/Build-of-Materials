import csv
import math
import tkinter as tk
from tkinter import filedialog, ttk, messagebox


# ============================================================
# COMPONENT BOX
# ============================================================
class ComponentBox:
    def __init__(self, app, canvas, ref, x, y, angle, value="", unit="", comp_type="Unknown", highlight=None):
        self.app = app
        self.canvas = canvas
        self.ref = ref
        self.x = x
        self.y = y
        self.angle = float(angle)
        self.value = value
        self.unit = unit
        self.comp_type = comp_type
        self.highlight = highlight

        self.width = 60
        self.height = 20

        self.rect = None
        self.label = None

        self.draw()
        self.bind_events()

    # -----------------------------------------------------------
    def formatted_label(self):
        if self.value and self.unit:
            return f"{self.ref} {self.value}{self.unit}"
        return self.ref

    # -----------------------------------------------------------
    def draw(self):
        w = self.width / 2
        h = self.height / 2

        # Rectangle corners
        corners = [
            (-w, -h),
            (w, -h),
            (w, h),
            (-w, h)
        ]

        theta = math.radians(self.angle)
        rotated = []

        for cx, cy in corners:
            rx = cx * math.cos(theta) - cy * math.sin(theta)
            ry = cx * math.sin(theta) + cy * math.cos(theta)
            rotated.append((self.x + rx, self.y + ry))

        pts = [coord for xy in rotated for coord in xy]

        # Highlight color logic
        fill = "lightblue"
        if self.highlight == "value":
            fill = "yellow"
        elif self.highlight == "unit":
            fill = "orange"
        elif self.highlight == "both":
            fill = "red"

        self.rect = self.canvas.create_polygon(pts, fill=fill, outline="black", width=2)

        # -----------------------------------------------------------
        # YOUR UPDATED LABEL PLACEMENT LOGIC
        # -----------------------------------------------------------
        angle = self.angle % 360
        offset = 6

        if 315 <= angle or angle < 45:
            lx, ly = self.x, self.y + h + offset
        elif 45 <= angle < 135:
            lx, ly = self.x, self.y + 30 + offset
        elif 135 <= angle < 225:
            lx, ly = self.x, self.y + h + offset
        else:
            lx, ly = self.x, self.y + 30 + offset

        self.label = self.canvas.create_text(lx, ly, text=self.formatted_label(), font=("Arial", 9))

    # -----------------------------------------------------------
    # RIGHT CLICK EDITOR
    # -----------------------------------------------------------
    def bind_events(self):
        self.canvas.tag_bind(self.rect, "<Button-3>", self.open_editor)
        self.canvas.tag_bind(self.label, "<Button-3>", self.open_editor)

    def open_editor(self, event):
        popup = tk.Toplevel()
        popup.title(f"Edit {self.ref}")

        tk.Label(popup, text=f"Reference: {self.ref}", font=("Arial", 12, "bold")).pack(pady=5)

        # TYPE
        tk.Label(popup, text="Component Type:").pack()
        type_box = ttk.Combobox(
            popup,
            values=["Resistor", "Capacitor", "Inductor", "Unknown"],
            state="readonly"
        )
        type_box.set(self.comp_type)
        type_box.pack()

        # VALUE
        tk.Label(popup, text="Value:").pack()
        value_entry = tk.Entry(popup)
        value_entry.insert(0, self.value)
        value_entry.pack()

        # UNITS
        tk.Label(popup, text="Units:").pack()
        unit_box = ttk.Combobox(
            popup,
            values=["pF", "nF", "uF", "pH", "nH", "Ohms"],
            state="readonly"
        )
        unit_box.set(self.unit)
        unit_box.pack()

        # ANGLE
        tk.Label(popup, text="Angle:").pack()
        angle_entry = tk.Entry(popup)
        angle_entry.insert(0, str(self.angle))
        angle_entry.pack()

        def apply_changes():
            new_type = type_box.get()

            # AUTO-UNIT BEHAVIOR (OPTION A)
            default_units = {
                "Capacitor": "nF",
                "Resistor": "Ohms",
                "Inductor": "nH",
                "Unknown": ""
            }

            new_unit = default_units[new_type]

            # update internal state
            self.comp_type = new_type
            self.value = value_entry.get()
            self.unit = new_unit
            self.angle = float(angle_entry.get())

            # update back-end file storage
            db = self.app.file_a if self.app.view_mode == "A" else self.app.file_b

            db[self.ref]["value"] = self.value
            db[self.ref]["unit"] = self.unit
            db[self.ref]["angle"] = self.angle
            db[self.ref]["comp_type"] = self.comp_type

            # redraw
            self.canvas.delete(self.rect)
            self.canvas.delete(self.label)
            self.draw()
            self.bind_events()

            popup.destroy()

        tk.Button(popup, text="Save Changes", command=apply_changes).pack(pady=10)


# ============================================================
# MAIN APPLICATION
# ============================================================
class LayoutApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BOM / Layout Comparator")

        self.file_a = None
        self.file_b = None
        self.view_mode = "A"

        # ---------- TOP BUTTON BAR ----------
        top = tk.Frame(root)
        top.pack(fill="x", pady=5)

        tk.Button(top, text="Load File A", command=self.load_file_a).pack(side="left", padx=5)
        tk.Button(top, text="Load File B", command=self.load_file_b).pack(side="left", padx=5)
        tk.Button(top, text="Save File A", command=self.save_file_a).pack(side="left", padx=5)
        tk.Button(top, text="Save File B", command=self.save_file_b).pack(side="left", padx=5)
        tk.Button(top, text="Toggle A/B", command=self.toggle_view).pack(side="left", padx=5)
        tk.Button(top, text="Show Differences", command=self.show_diff_table).pack(side="left", padx=5)
        tk.Button(top, text="Clear", command=self.clear_canvas).pack(side="left", padx=5)

        # ---------- BANNER ----------
        self.banner = tk.Label(
            root,
            text="VIEWING: FILE A",
            font=("Arial", 16, "bold"),
            bg="#4a90e2",  # blue
            fg="white"
        )
        self.banner.pack(fill="x")

        # ---------- CANVAS in FRAMED BORDER ----------
        self.canvas_frame = tk.Frame(root, bd=5, relief="solid")
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="white")
        self.canvas.pack(fill="both", expand=True)

    # ============================================================
    def update_view_indicator(self):
        if self.view_mode == "A":
            self.banner.config(text="VIEWING: FILE A", bg="#4a90e2")
            self.canvas_frame.config(
                highlightbackground="#4a90e2", highlightcolor="#4a90e2", highlightthickness=4
            )
        else:
            self.banner.config(text="VIEWING: FILE B", bg="#f39c12")
            self.canvas_frame.config(
                highlightbackground="#f39c12", highlightcolor="#f39c12", highlightthickness=4
            )

    # ============================================================
    def safe_float(self, v):
        if v is None:
            return None
        v = v.strip()
        if v == "":
            return None
        try:
            return float(v)
        except:
            return None

    # ============================================================
    def detect_type_and_unit(self, ref):
        first = ref[0].upper()
        if first == "C":
            return "Capacitor", "nF"
        if first == "R":
            return "Resistor", "Ohms"
        if first == "L":
            return "Inductor", "nH"
        return "Unknown", ""

    # ============================================================
    def parse_csv(self, fp):
        data = {}

        with open(fp, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for r in reader:
                ref = r.get("ReferenceID", "").strip()
                if not ref:
                    continue

                x = self.safe_float(r.get("X"))
                y = self.safe_float(r.get("Y"))

                if x is None or y is None:
                    continue

                angle = self.safe_float(r.get("Angle"))
                value = r.get("Value", "").strip()
                unit = r.get("Unit", "").strip()

                comp_type, default_unit = self.detect_type_and_unit(ref)

                if not unit:
                    unit = default_unit

                data[ref] = {
                    "x": x,
                    "y": y,
                    "angle": angle if angle is not None else 0.0,
                    "value": value,
                    "unit": unit,
                    "comp_type": comp_type
                }

        return data

    # ============================================================
    def load_file_a(self):
        fp = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not fp:
            return
        self.file_a = self.parse_csv(fp)
        self.view_mode = "A"
        self.redraw()

    def load_file_b(self):
        fp = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not fp:
            return
        self.file_b = self.parse_csv(fp)

        if not self.validate_files():
            self.file_b = None
            return

        messagebox.showinfo("Loaded", "File B loaded and validated.")
        self.redraw()

    # ============================================================
    def save_file_a(self):
        if not self.file_a:
            return
        self.save_to_csv(self.file_a, "Save File A")

    def save_file_b(self):
        if not self.file_b:
            messagebox.showerror("Error", "File B not loaded.")
            return
        self.save_to_csv(self.file_b, "Save File B")

    def save_to_csv(self, data, title):
        path = filedialog.asksaveasfilename(defaultextension=".csv", title=title)
        if not path:
            return

        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ReferenceID", "X", "Y", "Angle", "Value", "Unit"])

            for ref, info in data.items():
                w.writerow([
                    ref,
                    round(info["x"], 4),
                    round(info["y"], 4),
                    info["angle"],
                    info["value"],
                    info["unit"]
                ])

        messagebox.showinfo("Saved", f"Saved to: {path}")

    # ============================================================
    def validate_files(self):
        if self.file_a is None:
            messagebox.showerror("Error", "Load File A first.")
            return False

        if set(self.file_a.keys()) != set(self.file_b.keys()):
            messagebox.showerror("Error", "Component mismatch — wrong board.")
            return False

        for ref in self.file_a:
            a = self.file_a[ref]
            b = self.file_b[ref]
            if abs(a["x"] - b["x"]) > 0.1 or abs(a["y"] - b["y"]) > 0.1:
                messagebox.showerror("Error", f"Position mismatch at {ref}. Wrong revision.")
                return False

        return True

    # ============================================================
    def toggle_view(self):
        if self.file_a is None:
            return
        if self.file_b is None:
            messagebox.showerror("Error", "Load File B first.")
            return

        self.view_mode = "B" if self.view_mode == "A" else "A"
        self.redraw()

    # ============================================================
    def diff_info(self):
        diffs = {}
        for ref in self.file_a:
            a = self.file_a[ref]
            b = self.file_b[ref]

            v = a["value"] != b["value"]
            u = a["unit"] != b["unit"]

            if v and u:
                diffs[ref] = "both"
            elif v:
                diffs[ref] = "value"
            elif u:
                diffs[ref] = "unit"

        return diffs

    # ============================================================
    def redraw(self):
        self.clear_canvas(draw_only=True)
        self.update_view_indicator()

        data = self.file_a if self.view_mode == "A" else self.file_b
        diffinfo = None if self.view_mode == "A" else self.diff_info()

        xs = [data[r]["x"] for r in data]
        ys = [data[r]["y"] for r in data]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        w = max_x - min_x
        h = max_y - min_y

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        sx = (cw - 200) / w if w else 1
        sy = (ch - 200) / h if h else 1
        scale = min(sx, sy)

        for ref in data:
            info = data[ref]

            x = (info["x"] - min_x) * scale + 100
            y = (info["y"] - min_y) * scale + 100

            ComponentBox(
                self,
                self.canvas,
                ref,
                x,
                y,
                info["angle"],
                value=info["value"],
                unit=info["unit"],
                comp_type=info["comp_type"],
                highlight=diffinfo.get(ref) if diffinfo else None
            )

    # ============================================================
    def show_diff_table(self):
        if not self.file_a or not self.file_b:
            return

        diffs = self.diff_info()

        if not diffs:
            messagebox.showinfo("Identical", "No differences detected.")
            return

        win = tk.Toplevel()
        win.title("Differences")

        tree = ttk.Treeview(win, columns=("oldv", "oldu", "newv", "newu"), show="headings")
        tree.pack(fill="both", expand=True)

        tree.heading("oldv", text="Old Value")
        tree.heading("oldu", text="Old Unit")
        tree.heading("newv", text="New Value")
        tree.heading("newu", text="New Unit")

        for ref in sorted(diffs.keys()):
            a = self.file_a[ref]
            b = self.file_b[ref]
            tree.insert("", "end", values=(a["value"], a["unit"], b["value"], b["unit"]))

    # ============================================================
    def clear_canvas(self, draw_only=False):
        self.canvas.delete("all")
        if not draw_only:
            self.file_a = None
            self.file_b = None


# ============================================================
# RUN APP
# ============================================================
root = tk.Tk()
app = LayoutApp(root)
root.mainloop()
