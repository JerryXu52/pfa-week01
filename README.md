# Maya 2026 Procedural Random Generation Tool

**What it does:** `RandomGenerationTool.py` is a Maya 2026 tool that scatters a user-defined number of polygon primitives (cubes, spheres and cylinders) at completely random positions and rotations, assigns each one a procedurally coloured Lambert shader, and groups them all under `RandomCity_GRP` so the whole set can be cleared in a single click.

**How to run it:** Inside Maya, paste the script into a Python tab of the Script Editor and press Execute; from an external terminal, first open Maya's command port with `cmds.commandPort(name='127.0.0.1:7002', sourceType='mel')` and then run `python3 RandomGenerationTool.py`, which sends the script to Maya over a TCP socket — either route opens the same UI window, where four sliders control object count, spread, size and colour randomness.

**What I'd change:** With more time I would pool a small set of shared shaders rather than building one Lambert network per object (50 objects currently means 50 shaders), and add a bounding-box overlap check so that scattered geometry no longer intersects itself.

**Recording:** [video link](https://youtu.be/tp5Vjp4liss)
