import csv
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from openpyxl import load_workbook, Workbook


# ============================================================
# VALUE + UNIT COMPARISON
# ============================================================

def values_match(v1, u1, v2, u2):
    return str(v1).strip() == str(v2).strip() and str(u1).strip() == str(u2).strip()


# ============================================================
# COMPONENT BOX
# ============================================================

class ComponentBox:
    def __init__(self, canvas, ref, x, y, angle,
                 comp_type="Unknown", value="", unit="", highlight=None):
        self.canvas = canvas
        self.ref = ref
        self.x = x
        self.y = y
        self.angle = float(angle)
        self.comp_type = comp_type
        self.value = value
        self.unit = unit
        self.highlight = highlight

        self.width = 60
        self.height = 20

        self.rect = None
        self.label = None

        self.draw()
        self.bind_events()

    def formatted_label(self):
        if self.value and self.unit:
            return f"{self.ref} {self.value}{self.unit}"
        elif self.value:
            return f"{self.ref} {self.value}"
        return self.ref

    def draw(self):
        # Rectangle corners before rotation
        w = self.width / 2
        h = self.height / 2
        corners = [(-w, -h), (w, -h), (w, h), (-w, h)]

        theta = math.radians(self.angle)
        rotated = []
        for (cx, cy) in corners:
            rx = cx * math.cos(theta) - cy * math.sin(theta)
            ry = cx * math.sin(theta) + cy * math.cos(theta)
            rotated.append((self.x + rx, self.y + ry))

        points = [p for pt in rotated for p in pt]

        if self.highlight == "missing":
            color = "red"
        elif self.highlight == "mismatch":
            color = "yellow"
        else:
            color = "lightblue"

        self.rect = self.canvas.create_polygon(
            points, fill=color, outline="black", width=2
        )

        # Label placement based on angle
        angle = self.angle % 360
        offset = 6
        side_offset = 12

        if 315 <= angle or angle < 45:
            lx, ly = self.x, self.y + h + offset
        elif 45 <= angle < 135:
            lx, ly = self.x, self.y + 30 + offset
        elif 135 <= angle < 225:
            lx, ly = self.x, self.y - h - offset
        else:
            lx, ly = self.x - w - side_offset, self.y

        self.label = self.canvas.create_text(
            lx, ly, text=self.formatted_label(), font=("Arial", 9)
        )

    def bind_events(self):
        for tag in (self.rect, self.label):
            self.canvas.tag_bind(tag, "<Button-3>", self.right_click)

    def right_click(self, event):
        popup = tk.Toplevel()
        popup.title(f"Edit {self.ref}")

        tk.Label(popup, text=f"Reference: {self.ref}").pack(pady=5)

        tk.Label(popup, text="Value:").pack()
        val_entry = tk.Entry(popup)
        val_entry.insert(0, self.value)
        val_entry.pack()

        tk.Label(popup, text="Unit:").pack()
        unit_box = ttk.Combobox(
            popup,
            values=["pF", "nF", "uF", "pH", "nH", "Ohms"]
        )
        unit_box.set(self.unit)
        unit_box.pack()

        tk.Label(popup, text="Angle:").pack()
        ang_entry = tk.Entry(popup)
        ang_entry.insert(0, str(self.angle))
        ang_entry.pack()

        def save():
            try:
                self.value = val_entry.get()
                self.unit = unit_box.get()
                self.angle = float(ang_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Angle must be a number.")
                return

            self.canvas.delete(self.rect)
            self.canvas.delete(self.label)
            self.draw()
            self.bind_events()
            popup.destroy()

        tk.Button(popup, text="Save", command=save).pack(pady=10)


# ============================================================
# MAIN APPLICATION
# ============================================================

class LayoutApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chipset BOM + XY Layout Tool")

        self.xy_data = {}
        self.tuning_boms = []
        self.tuning_bom_names = []
        self.production_bom = None
        self.production_bom_headers = None

        # Fixed scale factor for XY positions
        self.scale_factor = 100

        # Top toolbar
        top = tk.Frame(root)
        top.pack(fill="x")

        tk.Button(top, text="Load XY File",
                  command=self.load_xy_file).pack(side="left", padx=5)
        tk.Button(top, text="Load Production BOM",
                  command=self.load_production_bom).pack(side="left", padx=5)
        tk.Button(top, text="Export Production BOM",
                  command=self.export_production_bom).pack(side="left", padx=5)
        tk.Button(top, text="Load Tuning BOM",
                  command=self.load_tuning_bom_csv).pack(side="left", padx=5)
        tk.Button(top, text="Apply Selected Tuning BOM",
                  command=self.apply_selected_tuning_bom).pack(side="left", padx=5)
        tk.Button(top, text="Save Tuning BOM",
                  command=self.save_tuning_bom_csv).pack(side="left", padx=5)
        tk.Button(top, text="Compare Tuning BOMs",
                  command=self.compare_tuning_boms).pack(side="left", padx=5)

        # Drawing canvas
        self.canvas = tk.Canvas(root, width=1500, height=900, bg="white")
        self.canvas.pack(fill="both", expand=True)

    # ========================================================
    # AUTO-UNIT ASSIGNER
    # ========================================================
    def auto_default_unit(self, ref, unit):
        """If a component has a value but no unit, auto-infer one."""
        if unit not in ["", None]:
            return unit

        r = ref.upper()
        if r.startswith("C"):
            return "nF"
        if r.startswith("R"):
            return "Ohms"
        if r.startswith("L"):
            return "nH"
        return ""

    # ========================================================
    # LOAD XY FILE (CSV)
    # ========================================================
    def load_xy_file(self):
        fp = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not fp:
            return

        data = {}
        try:
            with open(fp, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ref = (
                        row.get("ReferenceID")
                        or row.get("Reference")
                        or row.get("Ref")
                        or row.get("Designator")
                        or ""
                    ).strip()

                    if not ref:
                        continue

                    try:
                        x = float((row.get("X") or "").strip())
                        y = float((row.get("Y") or "").strip())
                        angle = float((row.get("Angle") or "0").strip())
                    except ValueError:
                        continue

                    x *= self.scale_factor
                    y *= self.scale_factor

                    data[ref] = {
                        "ref": ref,
                        "x": x,
                        "y": y,
                        "angle": angle,
                        "value": "",
                        "unit": "",
                        "comp_type": self.detect_type(ref),
                    }
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load XY file:\n{e}")
            return

        self.xy_data = data
        messagebox.showinfo("Loaded", "XY file loaded.")
        self.redraw()

    # ========================================================
    # DETECT COMPONENT TYPE
    # ========================================================
    def detect_type(self, ref):
        r = ref.upper()
        if r.startswith("C"):
            return "Capacitor"
        if r.startswith("R"):
            return "Resistor"
        if r.startswith("L"):
            return "Inductor"
        return "Unknown"

    # ========================================================
    # LOAD PRODUCTION BOM
    # ========================================================
    def load_production_bom(self):
        fp = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if not fp:
            return

        bom, headers = self.parse_production_bom(fp)
        if bom is None:
            return

        self.production_bom = bom
        self.production_bom_headers = headers

        # Apply values/units to existing XY components
        for ref, info in self.xy_data.items():
            if ref in self.production_bom:
                bval = self.production_bom[ref].get("value", "")
                bunt = self.production_bom[ref].get("unit", "")
                if bval:
                    info["value"] = bval
                if bunt:
                    info["unit"] = bunt

        messagebox.showinfo("Loaded", "Production BOM applied.")
        self.redraw()

    # ========================================================
    # EXPORT PRODUCTION BOM
    # ========================================================
    def export_production_bom(self):
        if not self.production_bom:
            messagebox.showerror("Error", "No production BOM loaded.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            title="Export Production BOM",
        )
        if not save_path:
            return

        wb = Workbook()
        ws = wb.active

        # Write headers as they were read
        for c, header in enumerate(self.production_bom_headers, start=1):
            ws.cell(row=1, column=c, value=header)

        # Try to find ref/value/unit columns; fall back if missing
        try:
            col_ref = self.production_bom_headers.index("Reference Designator") + 1
        except ValueError:
            col_ref = 1

        try:
            col_val = self.production_bom_headers.index("Value") + 1
        except ValueError:
            col_val = 2

        try:
            col_unit = self.production_bom_headers.index("Unit") + 1
        except ValueError:
            col_unit = 3

        row = 2
        for ref, d in self.production_bom.items():
            ws.cell(row=row, column=col_ref, value=ref)
            ws.cell(row=row, column=col_val, value=d.get("value", ""))
            ws.cell(row=row, column=col_unit, value=d.get("unit", ""))
            row += 1

        wb.save(save_path)
        messagebox.showinfo("Saved", f"Production BOM exported:\n{save_path}")

    # ========================================================
    # PARSE PRODUCTION BOM (IGNORE QTY/UNIT FOR UNITS)
    # ========================================================
    def parse_production_bom(self, filepath):
        """
        - Detects header row automatically
        - Splits multi-reference cells (e.g. 'C10, C3')
        - Extracts numeric + unit from Value cell text ONLY
        - Ignores dedicated Unit column and 'Qty / Unit' for electrical units
        - Treats 0 as missing
        - Auto-assigns default unit when needed
        """
        try:
            wb = load_workbook(filepath, data_only=True)
            ws = wb.active
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open file:\n{e}")
            return None, None

        REF_KEYS = ["reference designator"]
        VALUE_KEYS = ["value"]

        header_row = None
        col_ref = col_val = None

        # Detect header row
        for r in range(1, 60):
            row_vals = [
                (c, str(ws.cell(r, c).value).strip().lower())
                for c in range(1, ws.max_column + 1)
                if ws.cell(r, c).value
            ]

            possible_ref = [c for c, t in row_vals if any(k in t for k in REF_KEYS)]
            possible_val = [c for c, t in row_vals if any(k in t for k in VALUE_KEYS)]

            if possible_ref and possible_val:
                header_row = r
                col_ref = possible_ref[0]
                col_val = possible_val[0]
                break

        if not header_row:
            messagebox.showerror("Error", "Could not find BOM header row.")
            return None, None

        # Preserve original header row for export
        headers = [
            ws.cell(header_row, c).value or ""
            for c in range(1, ws.max_column + 1)
        ]

        bom = {}

        for r in range(header_row + 1, ws.max_row + 1):
            ref_cell = ws.cell(r, col_ref).value
            val_cell = ws.cell(r, col_val).value

            if not ref_cell:
                continue

            # Split multi-reference cells: "C10, C3" etc.
            refs = (
                str(ref_cell)
                .replace(";", ",")
                .replace("/", ",")
                .replace(" ", ",")
                .split(",")
            )

            # Get last token from Value cell (so "2 2.5pF" -> "2.5pF")
            raw_val_str = str(val_cell).strip() if val_cell else ""
            parts = raw_val_str.split()
            raw_val_str = parts[-1] if parts else ""

            numeric = self.extract_numeric(raw_val_str)
            # ENFORCE: unit is inferred from value text only
            unit = self.extract_unit(raw_val_str, explicit_unit="")

            if numeric == "0":
                numeric = ""
                unit = ""
            else:
                # If still no unit, auto-assign based on ref prefix
                if refs:
                    unit = self.auto_default_unit(refs[0], unit)

            for ref in refs:
                ref = ref.strip()
                if not ref:
                    continue
                bom[ref] = {
                    "value": numeric,
                    "unit": unit,
                }

        return bom, headers

    # ========================================================
    # NUMERIC + UNIT HELPERS
    # ========================================================
    def extract_numeric(self, raw):
        if raw in ["", None]:
            return ""
        s = str(raw).lower().replace(" ", "")
        out = ""
        for ch in s:
            if ch.isdigit() or ch == ".":
                out += ch
        return out

    def extract_unit(self, raw, explicit_unit):
        # We intentionally ignore explicit_unit here in production BOM,
        # but the function supports it for tuning BOM or future use.
        if explicit_unit not in ["", None]:
            return str(explicit_unit).strip()

        if raw in ["", None]:
            return ""

        s = str(raw).lower()

        if "pf" in s:
            return "pF"
        if "nf" in s:
            return "nF"
        if "uf" in s or "μf" in s:
            return "uF"
        if "nh" in s:
            return "nH"
        if "uh" in s or "μh" in s:
            return "uH"
        if "ohm" in s or s.endswith("r"):
            return "Ohms"

        return ""

    # ========================================================
    # LOAD TUNING BOM (CSV)
    # ========================================================
    def load_tuning_bom_csv(self):
        fp = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not fp:
            return

        tuning = {}
        try:
            with open(fp, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ref = (
                        row.get("ReferenceID")
                        or row.get("Reference")
                        or row.get("Ref")
                        or ""
                    ).strip()
                    if not ref:
                        continue

                    raw_val = (row.get("Value") or "").strip()
                    raw_unit = (row.get("Unit") or "").strip()

                    parts = raw_val.split()
                    raw_val = parts[-1] if parts else ""

                    numeric = self.extract_numeric(raw_val)
                    # For tuning BOM, allow Unit column if provided;
                    # pass raw_unit as explicit_unit.
                    unit = self.extract_unit(raw_val, explicit_unit=raw_unit)

                    if numeric == "0":
                        numeric = ""
                        unit = ""
                    else:
                        unit = self.auto_default_unit(ref, unit)

                    tuning[ref] = {
                        "value": numeric,
                        "unit": unit,
                    }
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tuning BOM:\n{e}")
            return

        self.tuning_boms.append(tuning)
        self.tuning_bom_names.append(fp)
        messagebox.showinfo("Loaded", f"Tuning BOM loaded:\n{fp}")

    # ========================================================
    # SAVE TUNING BOM (CSV)
    # ========================================================
    def save_tuning_bom_csv(self):
        if not self.xy_data:
            messagebox.showerror("Error", "Load XY file first.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Save Tuning BOM",
        )
        if not save_path:
            return

        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ReferenceID", "X", "Y", "Angle", "Value", "Unit"])

            for ref, info in self.xy_data.items():
                writer.writerow([
                    ref,
                    info["x"] / self.scale_factor,
                    info["y"] / self.scale_factor,
                    info["angle"],
                    info.get("value", ""),
                    info.get("unit", ""),
                ])

        messagebox.showinfo("Saved", f"Tuning BOM saved:\n{save_path}")

    # ========================================================
    # APPLY SELECTED TUNING BOM
    # ========================================================
    def apply_selected_tuning_bom(self):
        if not self.tuning_boms:
            messagebox.showerror("Error", "No tuning BOMs loaded.")
            return

        win = tk.Toplevel()
        win.title("Apply Tuning BOM")

        tk.Label(win, text="Choose tuning BOM:").pack()

        names = [
            f"Tuning {i + 1}: {self.tuning_bom_names[i]}"
            for i in range(len(self.tuning_boms))
        ]

        sel = tk.StringVar()
        box = ttk.Combobox(win, textvariable=sel, values=names, width=60)
        box.pack()
        box.current(0)

        def do_apply():
            bom = self.tuning_boms[box.current()]
            for ref, info in self.xy_data.items():
                if ref in bom:
                    info["value"] = bom[ref]["value"]
                    info["unit"] = bom[ref]["unit"]
            win.destroy()
            self.redraw()

        tk.Button(win, text="Apply", command=do_apply).pack(pady=10)

    # ========================================================
    # COMPARE TUNING BOMs
    # ========================================================
    def compare_tuning_boms(self):
        if len(self.tuning_boms) < 2:
            messagebox.showerror("Error", "Load at least 2 tuning BOMs.")
            return

        win = tk.Toplevel()
        win.title("Compare Tuning BOMs")

        names = [
            f"Tuning {i + 1}: {self.tuning_bom_names[i]}"
            for i in range(len(self.tuning_boms))
        ]

        tk.Label(win, text="Select BOM A:").pack()
        selA = tk.StringVar()
        comboA = ttk.Combobox(win, textvariable=selA, values=names, width=60)
        comboA.pack()
        comboA.current(0)

        tk.Label(win, text="Select BOM B:").pack()
        selB = tk.StringVar()
        comboB = ttk.Combobox(win, textvariable=selB, values=names, width=60)
        comboB.pack()
        comboB.current(1 if len(self.tuning_boms) > 1 else 0)

        def do_compare():
            bomA = self.tuning_boms[comboA.current()]
            bomB = self.tuning_boms[comboB.current()]
            win.destroy()
            self.show_tuning_difference_table(bomA, bomB)

        tk.Button(win, text="Compare", command=do_compare).pack(pady=10)

    # ========================================================
    # DIFFERENCE TABLE UI
    # ========================================================
    def show_tuning_difference_table(self, bomA, bomB):
        win = tk.Toplevel()
        win.title("Tuning BOM Differences")

        tree = ttk.Treeview(
            win,
            columns=("ref", "A_val", "A_unit", "B_val", "B_unit"),
            show="headings",
        )
        tree.pack(fill="both", expand=True)

        tree.heading("ref", text="Reference")
        tree.heading("A_val", text="A Value")
        tree.heading("A_unit", text="A Unit")
        tree.heading("B_val", text="B Value")
        tree.heading("B_unit", text="B Unit")

        refs = sorted(set(bomA.keys()) | set(bomB.keys()))
        for ref in refs:
            A_val = bomA.get(ref, {}).get("value", "")
            A_unit = bomA.get(ref, {}).get("unit", "")
            B_val = bomB.get(ref, {}).get("value", "")
            B_unit = bomB.get(ref, {}).get("unit", "")

            if not values_match(A_val, A_unit, B_val, B_unit):
                tree.insert(
                    "", "end",
                    values=(ref, A_val, A_unit, B_val, B_unit)
                )

    # ========================================================
    # REDRAW CANVAS
    # ========================================================
    def redraw(self):
        """Clear and redraw all components based on xy_data."""
        self.canvas.delete("all")

        if not self.xy_data:
            return

        for ref, info in self.xy_data.items():
            val = info.get("value", "")
            unit = info.get("unit", "")
            angle = info.get("angle", 0)

            # Auto-fill units if value exists but unit missing
            if val and not unit:
                unit = self.auto_default_unit(ref, unit)
                info["unit"] = unit

            # Determine highlight mode
            highlight = None

            # Missing value → red
            if val in ["", None]:
                highlight = "missing"

            # Production BOM mismatch → yellow
            if self.production_bom and ref in self.production_bom:
                pval = self.production_bom[ref].get("value", "")
                punit = self.production_bom[ref].get("unit", "")
                if pval or punit:
                    if not values_match(val, unit, pval, punit):
                        highlight = "mismatch"

            ComponentBox(
                self.canvas,
                ref,
                info["x"],
                info["y"],
                angle,
                comp_type=info.get("comp_type", "Unknown"),
                value=val,
                unit=unit,
                highlight=highlight,
            )


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = LayoutApp(root)
    root.mainloop()
