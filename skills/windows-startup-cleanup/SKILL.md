---
name: windows-startup-cleanup
description: Use when scanning and safely removing a Windows startup script or launcher outside a project repository.
---

# Windows startup cleanup

1. Inspect the per-user Startup folder:
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
2. Resolve `.lnk` files with `WScript.Shell.CreateShortcut()` to identify their target executable, arguments, and working directory.
3. Inspect the target `.cmd`, `.bat`, `.ps1`, or `.vbs` before deleting it. Confirm which applications it starts.
4. Check other startup surfaces without changing them:
   - `HKCU:\Software\Microsoft\Windows\CurrentVersion\Run`
   - `HKLM:\Software\Microsoft\Windows\CurrentVersion\Run`
   - Scheduled-task action commands
5. Delete only the confirmed launcher script and its obsolete Startup-folder shortcut or exact registration. Do not remove the applications or unrelated startup entries.
6. Verify exact target names/paths are absent from the Startup folder, Run entries, and scheduled-task actions. Treat broad substring matches such as `MicrosoftEdgeAutoLaunch...` as false positives unless they point to the target script.
