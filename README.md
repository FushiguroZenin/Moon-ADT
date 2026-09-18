# Moon

Moon is a personal AI computer agent that observes a Windows PC, explains evidence, and proposes safe next steps. **Dera1.4** is Moon’s local runtime: it owns system access, diagnostics, permission checks, and verification. The optional local model explains evidence; it does not control the computer.

## Beta capabilities

- Live CPU, memory, storage, network, uptime, and process evidence
- Performance, Downloads, startup, hardware, and crash investigations
- Optional private local AI through Ollama and `llama3.1:8b`
- Evidence-backed chat and persistent local task history
- Proposal, preview, approval, and verified local move/copy flow
- Paired mobile companion with live read-only system snapshots

Moon does not silently delete files, edit settings, close applications, or perform unapproved actions.

## Install Moon on Windows

1. Download `Moon-Setup.exe` from the GitHub Release.
2. Run the installer and open Moon.
3. Use diagnostics immediately, or choose **Enable local AI** to install Ollama and Moon’s recommended model.
4. To view live PC evidence on another device, open **Set up pairing**, configure the Moon relay, generate a one-time code, and enter it on the Moon web page.

The runtime installs at `%LOCALAPPDATA%\Moon\MoonRuntime.exe` and serves locally at `http://127.0.0.1:8765`. Keep it running for live paired-device updates.

## Privacy and permissions

Moon runs on the PC it observes. Paired web access is opt-in and uses an outbound HTTPS relay; Moon never opens an inbound internet port on the PC. The paired web view has read-only access to the evidence that the runtime publishes. Sensitive file operations remain local and require a proposal, dry-run preview, explicit approval, separate execution, and verification.

## For developers

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python run_api.py
```

The public web shell is in `frontend/`. The relay uses `Dockerfile.relay`. See [LABNOTE.md](LABNOTE.md) for architecture, deployment, and current limits.

## Beta release checklist

Before publishing a GitHub Release:

1. Build `installer-output\Moon-Setup.exe` with `installer\build-installer.ps1`.
2. Test it from a clean Windows profile or second PC: install, start runtime, load dashboard, pair a browser, and verify live CPU/memory/storage values.
3. Record the version and known limitations in `frontend\release-notes.html`.
4. Attach `Moon-Setup.exe` and a SHA-256 checksum to the GitHub Release.
5. Keep `MOON_RELAY_SESSION_SECRET` only in Render; never commit it.