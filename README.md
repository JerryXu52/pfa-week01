# Maya 2026 Procedural Random Generation Tool

An automated procedural geometry and shading tool for Autodesk Maya 2026. Built with Python 3 and `maya.cmds`, this tool generates randomized procedural cityscapes or abstract 3D geometry scatters, complete with dynamically generated Lambert shaders, customizable parameters, and built-in scene cleanup.

---

## Key Features

* **Dual Execution Modes:** Run directly inside Maya's Script Editor or launch externally from a system terminal via socket communication.
* **Procedural Mesh Generation:** Creates randomized poly cubes, spheres, and cylinders with custom sizing logic.
* **Dynamic HSV Shading:** Generates fresh Lambert shaders per object with procedural color palettes (HSV-to-RGB) and subtle incandescent illumination.
* **Full & Ground-Locked Scatter:** Supports both unconstrained 3D space scattering and ground-plane bounding box snapping (City Mode).
* **Non-Destructive Sizing:** Position and rotation are fully randomized on all three axes, while object scale is held at `(1.0, 1.0, 1.0)` so every polygon keeps the exact size it was built with.
* **Single-Chunk Undo Support:** All generation and cleanup actions are wrapped in `cmds.undoInfo` chunks for single-step `Ctrl+Z` operations.
* **Safe Scene Cleanup:** Wipes tool-generated geometry, shaders, and shading groups without altering existing user nodes.

---

## Requirements

* **Autodesk Maya 2026** (or Maya 2024+)
* **Python 3.x** (System Terminal & Maya internal Python environment)

---

## Quick Start & Usage

### Method 1: Launching from External Terminal (Command Port)

**Step 1.** Open Maya 2026 and enable the Command Port listener. Run the following in Maya's Script Editor (**Python tab**):

```python
import maya.cmds as cmds

if not cmds.commandPort('127.0.0.1:7002', query=True):
    cmds.commandPort(name='127.0.0.1:7002', sourceType='mel')
```

**Step 2.** Open your system Terminal (macOS/Linux) or Command Prompt (Windows), navigate to the script directory, and run:

```bash
python3 RandomGenerationTool.py
```

The terminal script encodes the tool into a Base64 payload, transmits it via TCP socket to port `7002`, and automatically draws the Maya UI.

**Optional flags:**

```bash
python3 RandomGenerationTool.py --host 127.0.0.1 --port 7002 --timeout 10
python3 RandomGenerationTool.py --help
```

---

### Method 2: Running Inside Maya's Script Editor

**Option A — Direct execution.** Open Maya's Script Editor (`Windows -> General Editors -> Script Editor`), open a new **Python** tab, load or paste `RandomGenerationTool.py`, and press **Execute**. The UI launches automatically.

**Option B — Import as a module.** Append the script folder to `sys.path` first, then import:

```python
import sys
sys.path.append(r"/path/to/folder/containing/the/script")

import RandomGenerationTool
RandomGenerationTool.show_ui()
```

---

## Core Maya Operations (MEL vs. Python Mapping)

This tool fulfills all core assignment requirements by translating 10 fundamental MEL operations into native Python `maya.cmds` calls:

| # | Operation Description | MEL Equivalent Command | Python `maya.cmds` Implementation |
| --- | --- | --- | --- |
| **1** | Create Polygon Sphere | `polySphere -r 1 ...` | `cmds.polySphere(radius=..., name=...)` |
| **2** | Create Polygon Cube | `polyCube -w 1 -h 1 -d 1 ...` | `cmds.polyCube(width=..., height=..., depth=...)` |
| **3** | Create Polygon Cylinder | `polyCylinder -r 1 -h 2 ...` | `cmds.polyCylinder(radius=..., height=...)` |
| **4** | Translate Object | `move -a X Y Z` | `cmds.move(pos_x, pos_y, pos_z, absolute=True)` |
| **5** | Rotate Object | `rotate -a X Y Z` | `cmds.rotate(rot_x, rot_y, rot_z, absolute=True)` |
| **6** | Scale Object | `scale -a X Y Z` | `cmds.scale(1.0, 1.0, 1.0, absolute=True)` |
| **7** | Create Shader Node | `shadingNode -asShader lambert` | `cmds.shadingNode("lambert", asShader=True)` |
| **8** | Assign Shader to Mesh | `sets -edit -forceElement <SG>` | `cmds.sets(obj, edit=True, forceElement=shading_group)` |
| **9** | Connect Node Attributes | `connectAttr outColor surfaceShader` | `cmds.connectAttr(shader + ".outColor", sg + ".surfaceShader")` |
| **10** | Group & Parent Nodes | `select ...; group -n "RandomCity_GRP"` | `cmds.select(created); cmds.group(name="RandomCity_GRP")` |

> **Note on Operation 6:** Scale is applied as an absolute identity transform. This guarantees a clean unit scale on every generated primitive (resetting any inherited non-unit scale) while ensuring no polygon is resized after creation.

---

## UI Parameters Reference

| Control Name | Type | Range / Options | Description |
| --- | --- | --- | --- |
| **Object Count** | Slider / Field | `1` to `50` | Total number of procedural primitive meshes to instantiate. |
| **Spread** | Slider / Field | `1.0` to `100.0` (field accepts up to `500.0`) | Half-width of the 3D distribution volume in scene units. |
| **Object Size** | Slider / Field | `0.1` to `20.0` (field accepts up to `100.0`) | Base size for generated geometry. Each object is built at `0.4x` to `1.8x` this value for natural variation. |
| **Colour Randomness** | Slider / Field | `0.0` to `10.0` | `0.0` yields cohesive hues; `10.0` creates fully randomized palettes. |
| **Random Seed** | Integer Field | `0` (Disabled) or `1+` | Set to `0` for continuous randomness; non-zero values enable reproducible scatters. |
| **Ground Plane Lock** | Checkbox | `True` / `False` | When checked (City Mode), object Y-positions snap to the ground grid via bounding box calculations. Unchecked by default. |
| **Generate Button** | Action Button | — | Triggers procedural geometry and shader generation. |
| **Clear Scene** | Action Button | — | Safely deletes tool-generated nodes (`RandomCity_GRP`, `randGeo_*`, `randMat_*`). |
| **Reset Settings** | Action Button | — | Restores all UI sliders and inputs to factory default values. |

---

## File Architecture

```text
pfa-week01/
├── RandomGenerationTool.py   # Primary executable script (Dual-mode GUI & Socket launcher)
├── env-report.md             # Environment installation & error resolution log
└── README.md                 # Technical documentation & usage instructions
```

---

## Troubleshooting

| Issue | Cause | Resolution |
| --- | --- | --- |
| `ConnectionRefusedError` in terminal | Maya's command port is not open. | Run the Step 1 snippet inside Maya before launching from the terminal. |
| Nothing happens after sending | Port opened with the wrong source type. | The port must be opened with `sourceType='mel'`, not `'python'`. |
| `ImportError: No module named maya` | The script was run with system Python. | This is expected outside Maya. The script automatically switches to socket-launcher mode. |
| Objects overlap or intersect | Full 3D randomization is enabled. | Enable **Ground Plane Lock** for a structured cityscape layout, or increase **Spread**. |
