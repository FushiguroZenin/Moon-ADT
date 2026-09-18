# Building the Moon Windows installer

Moon V1 uses a per-user local runtime, not a Windows service. The installer
places `MoonRuntime.exe` under the user's Local AppData folder and creates a
startup entry that runs it in the background on sign-in. The installer opens the
first-run setup page at `http://127.0.0.1:8765/app/setup.html`; later launches
open the Moon dashboard directly.

On Windows, the packaged runtime also lives in the system tray. Its menu can
open Moon, reopen setup, confirm that the localhost runtime is reachable, or
quit Moon cleanly. The startup entry launches the same tray runtime without
opening a browser window.

## Build prerequisites

- Windows 10 or 11
- The Moon project virtual environment
- Inno Setup 6

## Build

From PowerShell in the project folder:

```powershell
.\installer\build-installer.ps1
```

The script installs PyInstaller into the project environment, bundles
`MoonRuntime.exe` with the frontend assets, then invokes Inno Setup. The result
is `installer-output\Moon-Setup.exe`.

## V1 behavior

The installed runtime starts diagnostics and the local dashboard without Ollama.
The first-run page lets users install Ollama separately if they choose local AI
conversation. The runtime binds to localhost only. It does not create an inbound
network port, install a system-wide service, or permit file actions in the
packaged V1 runtime. Move and copy endpoints are blocked in guidance-only mode;
Moon explains safe manual steps instead.

The installer has a stable per-user application identity, so a newer installer
updates the existing Moon installation in place and retains its local data under
`%LOCALAPPDATA%\Moon`.

Before public distribution, code-sign the installer and test it on a clean
Windows account.
