# Environment Setup & Agent Report

**Agent Path Chosen**
- **Agent:** Claude Pro (Claude Opus 5)
- **Primary Software:** Autodesk Maya 2026 (macOS / Apple Silicon)
- **Execution Method:** Terminal execution via Python 3 + Socket connection to Maya Command Port (`127.0.0.1:7002`)

**What I Installed**
- Autodesk Maya 2026 (Educational Version)
- macOS System Python 3 & VS Code
- Git & GitHub repository (`pfa-week01`)

**What Broke and How I Fixed It**

**Issue 1: Socket Connection Refused when running script from Terminal**
- **Symptom:** Executing `python3 RandomGenerationTool.py` from the system terminal produced the error:
  `ERROR: could not reach Maya on 127.0.0.1:7002 [Errno 61] Connection refused`
- **Root Cause:** Maya 2026 does not open remote command socket ports by default for security reasons. The terminal launcher could not talk to Maya because port 7002 was not listening.
- **Fix:** Opened Maya 2026's internal Script Editor (Python tab) and manually ran the following code to open the MEL command port before triggering the script from terminal:
  ```python
  import maya.cmds as cmds
  if not cmds.commandPort('127.0.0.1:7002', query=True):
      cmds.commandPort(name='127.0.0.1:7002', sourceType='mel')
