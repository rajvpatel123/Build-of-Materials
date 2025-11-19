Chipset Layout & BOM Comparator
Interactive Python/Tkinter tool for loading, editing, and comparing BOM layout files

This application provides a fast and technician-friendly way to:

  ✅ Load and view chipset layout CSV files
  ✅ Auto-detect component types & default units (C/R/L)
  ✅ Visually edit components directly on the canvas
  ✅ Toggle between File A (Golden Reference) and File B (Unit Under Test)
  ✅ Highlight differences between the two files
  ✅ Display a differences table
  ✅ Save updated BOMs
  ✅ Provide clear visual indicators for active view (File A or File B)



 Features
🔹 Load & Visualize Layout CSV Files

    Each CSV contains:
    
    ReferenceID	X	Y	Angle	Value	Unit
    
    The app automatically:
    
    Places each component on a 2D canvas
    
    Applies rotation
    
    Draws components as rectangles
    
    Adds readable auto-positioned labels
    
    Scales layouts to fit the screen

🔹 Component Auto-Detection (Smart Defaults)

    Components automatically get assigned a type and default unit:
    
    Prefix	Type	Default Unit
    C	Capacitor	nF
    R	Resistor	Ohms
    L	Inductor	nH
    
    Unknown prefixes default to blank units.

🔹 Right-Click Component Editing

    Right-click any component to edit:
    
    Component Type
    
    Value
    
    Units (auto-updates based on type)
    
    Rotation Angle
    
    Editing updates the underlying data in File A or File B, depending on which view is active.

🔹 Compare Mode (File A vs File B)
    
    Load two CSVs of the same product, and the application will:
    
    ✔ Validate matching layout (X/Y coordinates)
    
    If any coordinate mismatches → error (wrong product/revision)
    
    ✔ Toggle view with one button
    
    FILE A View: Reference/Baseline
    
    FILE B View: Unit under test, with differences highlighted
    
    ✔ Differences Highlighting
    
    Value mismatch → yellow
    
    Unit mismatch → orange
    
    Both mismatch → red

🔹 Differences Table

    One click shows a sortable table of:
    
    | ReferenceID | Old Value | Old Unit | New Value | New Unit |
    
    Only components with differences are shown.

🔹 Clear Visual Indicators (Banner + Border)

    When toggling between A and B:
    
    FILE A
    
    Blue banner
    
    Blue canvas border
    
    FILE B
    
    Orange banner
    
    Orange canvas border
    
    Makes it immediately obvious which file is active.
    
    🔹 Saving Files
    
    You can independently save:
    
    File A
    
    File B
    
    Any edits from the right-click editor are preserved.

📂 CSV Format Requirements

Your input CSV must include:

    ReferenceID,X,Y,Angle,Value,Unit
    C1,1200,3100,0,100,nF
    R5,800,400,90,10,Ohms
    ...


    Missing X/Y rows are automatically skipped so they do not clutter the canvas.

🛠 Installation
1. Install Python 3.10+

(3.12+ recommended)

2. Install required Tkinter dependency

      Most systems include Tkinter by default. On Linux:
      
      sudo apt-get install python3-tk

3. Run the tool:
      python BOM_Comparator.py

🎯 Usage Workflow
1. Load File A

Loads the Golden Reference

2. Load File B

Loads UUT (Unit Under Test) and performs automatic validation

3. Toggle A/B

Switches display between A and B

4. Review Differences

Color-coded highlights + table

5. Edit Values

Right-click any component → update type/value/unit/angle

6. Save File A or File B

Exports updated content to CSV
