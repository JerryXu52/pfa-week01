#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RandomGenerationTool.py
=======================================================================
Assessment 1 - Maya 2026 Random Generation Tool

A procedural "random city / random geometry" generator for Autodesk Maya
2026, driven by a maya.cmds user interface.

-----------------------------------------------------------------------
DUAL EXECUTION MODES
-----------------------------------------------------------------------
1) INSIDE MAYA (Script Editor, Python tab):

       import sys
       sys.path.append(r"/path/to/folder/containing/this/file")
       import RandomGenerationTool
       RandomGenerationTool.show_ui()

   ...or simply open this file in the Script Editor and hit "Execute".

2) FROM AN EXTERNAL TERMINAL:

       python3 RandomGenerationTool.py

   This connects to Maya's command port at 127.0.0.1:7002, ships the
   entire contents of this file across the socket, and asks Maya to
   execute it - which builds the UI inside the running Maya session.

   Maya must be listening first. Run this ONCE in Maya's Script Editor
   (MEL tab), or place it in your userSetup.mel:

       commandPort -name "127.0.0.1:7002" -sourceType "mel";

   Or from the Python tab:

       import maya.cmds as cmds
       cmds.commandPort(name="127.0.0.1:7002", sourceType="mel")

   Convenience: running `python3 RandomGenerationTool.py --help` from the
   terminal prints the available options (custom host/port, etc).

-----------------------------------------------------------------------
THE 10 CORE MAYA OPERATIONS USED (MEL -> Python translation)
-----------------------------------------------------------------------
   #   MEL                              maya.cmds
   1   polySphere                       cmds.polySphere()
   2   polyCube                         cmds.polyCube()
   3   polyCylinder                     cmds.polyCylinder()
   4   move                             cmds.move()
   5   rotate                           cmds.rotate()
   6   scale                            cmds.scale()
   7   shadingNode -asShader lambert    cmds.shadingNode()
   8   sets -e -forceElement <SG>       cmds.sets()            (assign shader)
   9   connectAttr                      cmds.connectAttr()
  10   select / group                   cmds.select() / cmds.group()

Author : Jerry
=======================================================================
"""

from __future__ import print_function

import os
import sys
import random
import colorsys

# ----------------------------------------------------------------------
# Maya availability detection.
# This single flag is what makes dual-execution safe: the __main__ block
# branches on it, so re-executing this file inside Maya never re-enters
# the socket client (which would otherwise loop forever).
# ----------------------------------------------------------------------
try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    MAYA_AVAILABLE = False


# ======================================================================
# CONFIGURATION
# ======================================================================

MAYA_HOST = "127.0.0.1"
MAYA_PORT = 7002

WINDOW_NAME = "randomGenerationToolWin"
WINDOW_TITLE = "Random Generation Tool  |  Assessment 1"

GROUP_NAME = "RandomCity_GRP"      # top-level group holding all output
MATERIAL_PREFIX = "randMat_"       # every generated shader starts with this
OBJECT_PREFIX = "randGeo_"         # every generated transform starts with this

# UI control names (kept as module constants so every function agrees)
CTRL_COUNT = "rgtCountSlider"
CTRL_SPREAD = "rgtSpreadSlider"
CTRL_SIZE = "rgtSizeSlider"
CTRL_COLOR = "rgtColorSlider"
CTRL_SEED = "rgtSeedField"
CTRL_GROUND = "rgtGroundCheck"
CTRL_STATUS = "rgtStatusText"

# Bounds for the fully-random transform pass.
ROT_MIN = 0.0          # full 360 rotation on every axis
ROT_MAX = 360.0

# Scale is deliberately NOT randomised: every generated polygon keeps the
# size it was built with. This value is applied verbatim so the scale
# operation is still exercised while remaining a no-op on the geometry.
NEUTRAL_SCALE = (1.0, 1.0, 1.0)


# ======================================================================
# SECTION 1 - MATERIAL CREATION
# ======================================================================

def random_color(randomness, base_hue=0.58):
    """Return an (r, g, b) tuple whose variety is driven by `randomness`.

    randomness = 0   -> every object gets essentially the same base colour
    randomness = 10  -> fully random hue, saturation and value

    Args:
        randomness (float): 0.0 - 10.0 colour-chaos factor from the UI.
        base_hue (float): hue used when randomness is low (0-1).

    Returns:
        tuple(float, float, float): linear RGB in the 0-1 range.
    """
    t = max(0.0, min(10.0, float(randomness))) / 10.0

    # Hue drifts away from the base hue as randomness rises.
    hue = (base_hue + random.uniform(-0.5, 0.5) * t) % 1.0
    # Saturation and value stay tame at low randomness, spread out at high.
    sat = 0.15 + (0.85 * t * random.random())
    val = 0.55 + (0.45 * random.random() * t) if t > 0.0 else 0.75

    return colorsys.hsv_to_rgb(hue, sat, val)


def create_material(randomness, index=0):
    """Build one Lambert shader + shading group and wire them together.

    Demonstrates operations #7 (shadingNode), #9 (connectAttr) and the
    shading-group half of #8.

    Args:
        randomness (float): 0-10 colour randomness from the UI slider.
        index (int): used only to make node names readable.

    Returns:
        tuple(str, str): (shader name, shading group name)
    """
    r, g, b = random_color(randomness)

    # --- OPERATION 7: shadingNode -asShader lambert -------------------
    shader = cmds.shadingNode(
        "lambert",
        asShader=True,
        name="{0}{1:03d}".format(MATERIAL_PREFIX, index)
    )
    cmds.setAttr(shader + ".color", r, g, b, type="double3")

    # A little incandescence variation so the "city" reads as lit windows.
    glow = random.random() * 0.15 * (randomness / 10.0)
    cmds.setAttr(shader + ".incandescence", r * glow, g * glow, b * glow,
                 type="double3")

    # Matching shading group (renderable set).
    shading_group = cmds.sets(
        renderable=True,
        noSurfaceShader=True,
        empty=True,
        name=shader + "SG"
    )

    # --- OPERATION 9: connectAttr -------------------------------------
    cmds.connectAttr(shader + ".outColor",
                     shading_group + ".surfaceShader",
                     force=True)

    return shader, shading_group


def assign_material(obj, shading_group):
    """Assign a shading group to a transform.

    Demonstrates operation #8 (sets -e -forceElement, the Python
    equivalent of MEL's `hyperShade -assign`).
    """
    cmds.sets(obj, edit=True, forceElement=shading_group)


# ======================================================================
# SECTION 2 - GEOMETRY CREATION
# ======================================================================

def create_primitive(kind, size):
    """Create one polygon primitive of the requested kind.

    Demonstrates operations #1 (polySphere), #2 (polyCube) and
    #3 (polyCylinder).

    Args:
        kind (str): one of "cube", "sphere", "cylinder".
        size (float): base radius / width for the primitive.

    Returns:
        str: the new transform node name.
    """
    if kind == "sphere":
        # --- OPERATION 1: polySphere ----------------------------------
        transform = cmds.polySphere(
            radius=size * 0.5,
            subdivisionsX=16,
            subdivisionsY=12,
            name=OBJECT_PREFIX + "sphere#"
        )[0]

    elif kind == "cylinder":
        # --- OPERATION 3: polyCylinder --------------------------------
        transform = cmds.polyCylinder(
            radius=size * 0.4,
            height=size * random.uniform(1.0, 4.0),
            subdivisionsX=14,
            name=OBJECT_PREFIX + "cylinder#"
        )[0]

    else:
        # --- OPERATION 2: polyCube ------------------------------------
        transform = cmds.polyCube(
            width=size,
            height=size * random.uniform(1.0, 6.0),
            depth=size,
            name=OBJECT_PREFIX + "cube#"
        )[0]

    return transform


def random_position(spread, ground=False, obj=None):
    """Return a fully random (x, y, z) world position.

    Args:
        spread (float): half-width of the scatter volume in scene units.
        ground (bool): when True the Y value is derived from the object's
            bounding box so it rests on the ground plane (city mode);
            when False, Y is randomised exactly like X and Z, so objects
            are scattered freely through 3D space.
        obj (str): transform to measure - only needed when ground is True.

    Returns:
        tuple(float, float, float)
    """
    pos_x = random.uniform(-spread, spread)
    pos_z = random.uniform(-spread, spread)

    if ground and obj is not None:
        bbox = cmds.exactWorldBoundingBox(obj)
        pos_y = (bbox[4] - bbox[1]) * 0.5
    else:
        pos_y = random.uniform(-spread, spread)

    return pos_x, pos_y, pos_z


def random_rotation():
    """Return a fully random (rx, ry, rz) Euler rotation in degrees.

    Every axis gets an independent 0-360 value, so orientation is
    unconstrained rather than the old yaw-only spin.
    """
    return (random.uniform(ROT_MIN, ROT_MAX),
            random.uniform(ROT_MIN, ROT_MAX),
            random.uniform(ROT_MIN, ROT_MAX))


def apply_neutral_scale(obj):
    """Explicitly hold an object at its original, unmodified size.

    Scale randomisation is intentionally absent: each polygon must keep
    the exact dimensions it was created with. An absolute scale of
    (1, 1, 1) is still applied so that the object's scale is guaranteed
    to be clean - if the primitive inherited a non-unit scale from the
    tool settings or an existing selection, this resets it - and so that
    the `scale` operation remains part of the tool's command coverage.

    Returns:
        tuple(float, float, float): always NEUTRAL_SCALE.
    """
    cmds.scale(NEUTRAL_SCALE[0], NEUTRAL_SCALE[1], NEUTRAL_SCALE[2],
               obj, absolute=True)
    return NEUTRAL_SCALE


def randomise_transform(obj, spread, size=None, ground=False):
    """Randomise one object's position and rotation, but NOT its size.

      * POSITION - random X, Y and Z across the full scatter volume
        (Y is instead computed from the bounding box when `ground` is
        True, which is the only constraint the tool ever applies).
      * ROTATION - random 0-360 degrees on X, Y and Z.
      * SCALE    - locked to (1, 1, 1). Every polygon retains the size
        it was built with; nothing here stretches, squashes or resizes
        the geometry.

    Demonstrates operations #4 (move), #5 (rotate) and #6 (scale).

    Args:
        obj (str): transform node to randomise.
        spread (float): half-width of the scatter volume.
        size (float): unused, retained for call-signature compatibility.
        ground (bool): keep objects sitting on the ground plane.

    Returns:
        dict: the values applied, useful for logging and verification.
    """
    # --- OPERATION 6: scale -------------------------------------------
    # Applied first and always neutral - the object keeps its original
    # size. Doing it here also means ground mode measures a bounding box
    # with a known-unit scale.
    scl = apply_neutral_scale(obj)

    # --- OPERATION 5: rotate ------------------------------------------
    rot = random_rotation()
    cmds.rotate(rot[0], rot[1], rot[2], obj, absolute=True)

    # --- OPERATION 4: move --------------------------------------------
    # Moved last: the bounding box used by ground mode is only correct
    # once the object's final orientation has been applied.
    pos = random_position(spread, ground=ground, obj=obj)
    cmds.move(pos[0], pos[1], pos[2], obj, absolute=True)

    return {"position": pos, "rotation": rot, "scale": scl}


def generate_geometry(count, spread, size, color_randomness, seed=None,
                      ground=False):
    """Core generation routine - the heart of the tool.

    Creates `count` randomised primitives, gives each a fresh randomised
    Lambert material, and parents the whole lot under a single group so
    the scene stays tidy and is trivially clearable.

    Args:
        count (int): number of objects to build (1-50).
        spread (float): half-width of the scatter area in scene units.
        size (float): base size of each primitive.
        color_randomness (float): 0-10 colour variety.
        seed (int or None): optional RNG seed for reproducible results.
        ground (bool): if True, objects are kept sitting on the ground
            plane (Y is derived from the bounding box). If False - the
            default - position and rotation are completely random on
            every axis. Object size is never randomised after creation
            in either mode.

    Returns:
        str: the name of the group node containing everything.
    """
    if seed is not None:
        random.seed(seed)

    count = int(max(1, count))
    kinds = ("cube", "sphere", "cylinder")
    created = []

    # Undo chunk so the whole generation collapses into one Ctrl+Z.
    cmds.undoInfo(openChunk=True, chunkName="RandomGeneration")
    try:
        for i in range(count):
            kind = random.choice(kinds)
            # Size is decided ONCE, here, at build time. Nothing
            # downstream rescales the object, so whatever dimensions the
            # primitive is created with are the dimensions it keeps.
            obj = create_primitive(kind, size * random.uniform(0.4, 1.8))
            randomise_transform(obj, spread, size, ground=ground)

            shader, shading_group = create_material(color_randomness, i)
            assign_material(obj, shading_group)

            created.append(obj)

        # --- OPERATION 10: select + group ------------------------------
        cmds.select(created, replace=True)
        if cmds.objExists(GROUP_NAME):
            # Append to the existing group rather than making GRP1, GRP2...
            cmds.parent(created, GROUP_NAME)
            group_node = GROUP_NAME
        else:
            group_node = cmds.group(created, name=GROUP_NAME)

        cmds.select(group_node, replace=True)
    finally:
        cmds.undoInfo(closeChunk=True)

    return group_node


# ======================================================================
# SECTION 3 - SCENE CLEARING
# ======================================================================

def clear_scene(*_args):
    """Delete every node this tool created: geometry, shaders and SGs.

    Deliberately conservative - it only touches nodes matching the
    tool's own naming conventions, so the user's other work survives.
    """
    deleted = 0

    cmds.undoInfo(openChunk=True, chunkName="RandomGenerationClear")
    try:
        # 1. The geometry group.
        if cmds.objExists(GROUP_NAME):
            cmds.delete(GROUP_NAME)
            deleted += 1

        # 2. Any stragglers that were un-parented by hand.
        strays = cmds.ls(OBJECT_PREFIX + "*", type="transform") or []
        if strays:
            cmds.delete(strays)
            deleted += len(strays)

        # 3. Shaders and their shading groups.
        shaders = cmds.ls(MATERIAL_PREFIX + "*", materials=True) or []
        sgs = cmds.ls(MATERIAL_PREFIX + "*SG") or []
        junk = [n for n in shaders + sgs if cmds.objExists(n)]
        if junk:
            cmds.delete(junk)
            deleted += len(junk)
    finally:
        cmds.undoInfo(closeChunk=True)

    set_status("Cleared {0} node(s).".format(deleted))
    return deleted


# ======================================================================
# SECTION 4 - USER INTERFACE
# ======================================================================

def set_status(message):
    """Write a line of feedback into the UI (and the Script Editor)."""
    print("[RandomGenerationTool] " + message)
    if MAYA_AVAILABLE and cmds.text(CTRL_STATUS, exists=True):
        cmds.text(CTRL_STATUS, edit=True, label=message)


def _on_generate(*_args):
    """Button 1 callback - read the sliders, then build the scene."""
    count = cmds.intSliderGrp(CTRL_COUNT, query=True, value=True)
    spread = cmds.floatSliderGrp(CTRL_SPREAD, query=True, value=True)
    size = cmds.floatSliderGrp(CTRL_SIZE, query=True, value=True)
    color = cmds.floatSliderGrp(CTRL_COLOR, query=True, value=True)
    seed = cmds.intFieldGrp(CTRL_SEED, query=True, value1=True)
    ground = cmds.checkBox(CTRL_GROUND, query=True, value=True)

    generate_geometry(
        count=count,
        spread=spread,
        size=size,
        color_randomness=color,
        seed=(seed if seed > 0 else None),
        ground=ground,
    )
    mode = "ground-locked" if ground else "fully random 3D"
    set_status("Generated {0} object(s) under '{1}'  ({2}).".format(
        int(count), GROUP_NAME, mode))


def _on_clear(*_args):
    """Button 2 callback."""
    clear_scene()


def _on_reset(*_args):
    """Restore every slider to its default value."""
    cmds.intSliderGrp(CTRL_COUNT, edit=True, value=15)
    cmds.floatSliderGrp(CTRL_SPREAD, edit=True, value=20.0)
    cmds.floatSliderGrp(CTRL_SIZE, edit=True, value=2.0)
    cmds.floatSliderGrp(CTRL_COLOR, edit=True, value=5.0)
    cmds.intFieldGrp(CTRL_SEED, edit=True, value1=0)
    cmds.checkBox(CTRL_GROUND, edit=True, value=False)
    set_status("Settings reset to defaults.")


def show_ui(*_args):
    """Build and display the tool window.

    Safe to call repeatedly - any previous instance is deleted first.
    """
    if not MAYA_AVAILABLE:
        raise RuntimeError(
            "show_ui() requires Maya. Run this file from a terminal to "
            "push it to a running Maya session over the command port."
        )

    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME, window=True)

    window = cmds.window(
        WINDOW_NAME,
        title=WINDOW_TITLE,
        widthHeight=(460, 340),
        sizeable=True,
    )

    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Random Generation Tool",
              font="boldLabelFont", align="center")
    cmds.text(label="Procedural city / geometry scatter with random shaders",
              align="center")
    cmds.separator(height=10, style="in")

    # --- Slider 1: object count ---------------------------------------
    cmds.intSliderGrp(
        CTRL_COUNT,
        label="Object Count",
        field=True,
        minValue=1, maxValue=50,
        fieldMinValue=1, fieldMaxValue=50,
        value=15,
        columnWidth3=(110, 60, 220),
        annotation="How many primitives to generate (1-50).",
    )

    # --- Slider 2: spacing / spread -----------------------------------
    cmds.floatSliderGrp(
        CTRL_SPREAD,
        label="Spread",
        field=True,
        minValue=1.0, maxValue=100.0,
        fieldMinValue=1.0, fieldMaxValue=500.0,
        value=20.0, precision=2,
        columnWidth3=(110, 60, 220),
        annotation="Half-width of the scatter area in scene units.",
    )

    # --- Slider 3: polygon size ---------------------------------------
    cmds.floatSliderGrp(
        CTRL_SIZE,
        label="Object Size",
        field=True,
        minValue=0.1, maxValue=20.0,
        fieldMinValue=0.1, fieldMaxValue=100.0,
        value=2.0, precision=2,
        columnWidth3=(110, 60, 220),
        annotation="Base size of each individual polygon primitive.",
    )

    # --- Slider 4: colour randomness ----------------------------------
    cmds.floatSliderGrp(
        CTRL_COLOR,
        label="Colour Randomness",
        field=True,
        minValue=0.0, maxValue=10.0,
        fieldMinValue=0.0, fieldMaxValue=10.0,
        value=5.0, precision=1,
        columnWidth3=(110, 60, 220),
        annotation="0 = near-uniform colour, 10 = fully random shaders.",
    )

    # --- Optional reproducibility seed --------------------------------
    cmds.intFieldGrp(
        CTRL_SEED,
        label="Random Seed",
        numberOfFields=1,
        value1=0,
        columnWidth2=(110, 60),
        annotation="0 = fresh randomness each run. Any other value is "
                   "reproducible.",
    )

    # --- Ground-plane constraint (off = completely random) ------------
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(110, 320),
                   columnAttach=[(1, "both", 0), (2, "both", 0)])
    cmds.text(label="")
    cmds.checkBox(
        CTRL_GROUND,
        label="Keep objects on ground plane (city mode)",
        value=False,
        annotation="OFF (default): position and rotation are completely "
                   "random on all three axes. ON: Y position is snapped "
                   "so objects rest on the grid. Object size is never "
                   "altered after creation in either mode.",
    )
    cmds.setParent("..")

    cmds.separator(height=10, style="in")

    # --- Buttons -------------------------------------------------------
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(215, 215),
                   columnAlign2=("center", "center"),
                   adjustableColumn=2,
                   columnAttach=[(1, "both", 2), (2, "both", 2)])

    cmds.button(
        label="Generate Random City / Geometries",
        height=42,
        backgroundColor=(0.30, 0.52, 0.36),
        command=_on_generate,
        annotation="Build randomised primitives with random materials.",
    )
    cmds.button(
        label="Clear Scene",
        height=42,
        backgroundColor=(0.58, 0.30, 0.30),
        command=_on_clear,
        annotation="Delete everything this tool created.",
    )
    cmds.setParent("..")

    cmds.button(label="Reset Settings", height=24, command=_on_reset)

    cmds.separator(height=8, style="in")
    cmds.text(CTRL_STATUS, label="Ready.", align="left")
    cmds.separator(height=8, style="none")

    cmds.setParent("..")
    cmds.showWindow(window)
    return window


# ======================================================================
# SECTION 5 - COMMAND PORT / SOCKET COMMUNICATION
# ======================================================================

def open_command_port(port=MAYA_PORT, host=MAYA_HOST):
    """Open Maya's MEL command port. Run this once INSIDE Maya.

    Handy helper so the marker can enable the terminal workflow with a
    single Python call instead of hunting for the MEL syntax.
    """
    if not MAYA_AVAILABLE:
        raise RuntimeError("open_command_port() must be run inside Maya.")

    name = "{0}:{1}".format(host, port)
    if cmds.commandPort(name, query=True):
        print("[RandomGenerationTool] Command port already open on " + name)
        return name

    cmds.commandPort(name=name, sourceType="mel", echoOutput=False)
    print("[RandomGenerationTool] Command port opened on " + name)
    return name


def _build_payload(script_text):
    """Wrap this file's source in a single, quote-safe MEL command.

    The source is base64-encoded so that newlines, quotes, backslashes and
    unicode in the script can never break out of the MEL string literal.
    Maya then decodes and execs it in its own Python interpreter.
    """
    import base64

    encoded = base64.b64encode(script_text.encode("utf-8")).decode("ascii")

    python_code = (
        "import base64;"
        "_src = base64.b64decode('{0}').decode('utf-8');"
        "_ns = {{'__name__': '__maya_remote__'}};"
        "exec(compile(_src, 'RandomGenerationTool.py', 'exec'), _ns);"
        "_ns['show_ui']()"
    ).format(encoded)

    # MEL: python("...") - the payload contains no quotes or newlines.
    return 'python("{0}");\n'.format(python_code)


def send_to_maya(host=MAYA_HOST, port=MAYA_PORT, script_path=None,
                 timeout=10.0):
    """Ship this script to a running Maya session over the command port.

    Args:
        host (str): Maya command-port host.
        port (int): Maya command-port port.
        script_path (str): file to send; defaults to this file.
        timeout (float): socket timeout in seconds.

    Returns:
        bool: True on success.
    """
    import socket

    if script_path is None:
        script_path = os.path.abspath(__file__)

    if not os.path.isfile(script_path):
        print("ERROR: cannot find script file: " + script_path)
        return False

    with open(script_path, "r", encoding="utf-8") as handle:
        script_text = handle.read()

    payload = _build_payload(script_text)

    print("-" * 66)
    print("Random Generation Tool - remote launcher")
    print("  script : {0}".format(script_path))
    print("  target : {0}:{1}".format(host, port))
    print("  bytes  : {0}".format(len(payload)))
    print("-" * 66)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        sock.connect((host, port))
        sock.sendall(payload.encode("utf-8"))

        # Maya replies with the command result (often empty). Not fatal
        # if nothing arrives before the timeout.
        try:
            reply = sock.recv(8192).decode("utf-8", errors="replace").strip()
            if reply:
                print("Maya replied: " + reply)
        except socket.timeout:
            pass

        print("SUCCESS: script sent. The tool window should now be open "
              "in Maya.")
        return True

    except (socket.timeout, ConnectionRefusedError, OSError) as err:
        print("ERROR: could not reach Maya on {0}:{1}".format(host, port))
        print("       {0}".format(err))
        print("")
        print("Open the command port inside Maya first.")
        print("  MEL   :  commandPort -name \"{0}:{1}\" -sourceType \"mel\";"
              .format(host, port))
        print("  Python:  import maya.cmds as cmds")
        print("           cmds.commandPort(name=\"{0}:{1}\", "
              "sourceType=\"mel\")".format(host, port))
        return False

    finally:
        sock.close()


# ======================================================================
# SECTION 6 - ENTRY POINT
# ======================================================================

def _parse_args(argv):
    """Minimal argument parsing for the terminal launcher."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Send RandomGenerationTool.py to a running Maya session "
                    "via the command port."
    )
    parser.add_argument("--host", default=MAYA_HOST,
                        help="Maya command-port host (default: %(default)s)")
    parser.add_argument("--port", type=int, default=MAYA_PORT,
                        help="Maya command-port port (default: %(default)s)")
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="Socket timeout in seconds (default: %(default)s)")
    return parser.parse_args(argv)


def main(argv=None):
    """Dual-mode entry point.

    Inside Maya  -> show the UI.
    Outside Maya -> push this file to Maya over the socket.
    """
    if MAYA_AVAILABLE:
        return show_ui()

    args = _parse_args(sys.argv[1:] if argv is None else argv)
    ok = send_to_maya(host=args.host, port=args.port, timeout=args.timeout)
    return 0 if ok else 1


if __name__ == "__main__":
    result = main()
    if not MAYA_AVAILABLE:
        sys.exit(result)
