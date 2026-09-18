# Moon

Moon is a personal AI computer agent. Dera1.4 is its controlled local runtime.

## First milestone

The current foundation is read-only. It collects a system snapshot and produces
deterministic performance findings for: "My computer is slow. Find out why."

## Run

Select the project virtual environment in PyCharm, install dependencies, then run:

```powershell
pip install -e .
python main.py status --json
python main.py diagnose performance --json
python main.py investigate slow-computer --json
python main.py inspect "C:\Users\Indra\Downloads" --json
python main.py propose cleanup-downloads --json
```

`investigate slow-computer` saves a local task record to `data/moon.db`. It only
observes and diagnoses; no model integration or computer-changing actions are included yet.

`inspect` lists the largest files, subfolders, and file types in a user-owned directory.
It rejects paths outside the current user's home directory.

`propose cleanup-downloads` creates reviewable cleanup proposals only. Execution is disabled.

Run `propose cleanup-downloads` first and copy an actual `id` from its `proposals`
list. Then run `approve ACTUAL_ID DESTINATION`, followed by `execute ACTUAL_ID`.
Both source and destination must be within the current user's home directory.
Moon currently offers moves only. Permanent deletion is not implemented or proposed.

Use `dismiss PROPOSAL_ID` to remove an unacted proposal from Moon's local queue.

Run `preview ACTUAL_ID` after approval to validate the move without changing files.

## Local 8B reasoning

Moon uses Ollama as its first replaceable local-model runtime. Install and start
Ollama with `llama3.1:8b`, then run `python main.py explain-slow --json`.
The model only explains a fresh read-only investigation; Dera1.4 keeps control of
tools, permissions, and actions. Set `MOON_MODEL` to use a different Ollama model.
Use `--debug` with `explain-slow` to inspect a rejected local model response.

### Local AI for installed Moon

The installed runtime opens a setup page with an **Enable local AI** choice. It
first explains that the recommended model stays on the PC, consumes several GB of
disk space, and uses additional RAM while active. If Ollama is absent, Moon opens
the official Ollama installer. Once it is installed, the user explicitly starts
the model download and sees its preparation progress on the setup page. Moon’s
diagnostics work without local AI; the model is recommended for natural,
evidence-grounded conversations.

## Conversational routing

Use `ask` for a small, validated natural-language interface:

```powershell
python main.py ask "Moon, my computer is slow. Find out why." --json
```

The model can only select from existing Dera1.4 intents: system status, slow-computer
investigation, Downloads inspection, Downloads proposal review, and explanation.

## Windows applications and startup

```powershell
python main.py diagnose applications --json
python main.py ask "Why does my computer take so long to start?" --json
```

This read-only diagnostic lists current-user and all-users registry startup entries,
current-user Startup-folder items, and installed Windows applications.

Use `inspect-startup "ENTRY_NAME"` for metadata on a specific entry, or `propose startup`
for review-only suggestions. Startup changes are not implemented.

## Application crashes

```powershell
python main.py investigate crash chrome.exe --json
```

Moon reads recent Windows Application crash reports for a validated application name.
It records faulting application/module details as a read-only task.

## Hardware and connectivity

```powershell
python main.py diagnose hardware --json
```

Moon reports battery, network-interface, and NVIDIA GPU telemetry where available.

## Proactive monitoring

```powershell
python main.py monitor check
```

The first check establishes a local baseline. Later checks compare free storage,
memory use, and startup entries. Moon reports meaningful changes only and never acts.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Local API

```powershell
python -m pip install -e .[api]
python run_api.py
```

The Dera1.4 API binds only to `http://127.0.0.1:8765`. Open
`http://127.0.0.1:8765/docs` for the local API documentation. It exposes system
status, investigations, task history, monitoring, Downloads inspection, and proposal
preview. Approval and execution are intentionally not exposed over HTTP yet.

## Device pairing foundation

The local API has pairing endpoints for a future Moon web client: status, one-time
code creation, and local pairing completion. Pairing codes expire after ten minutes;
only token hashes are retained locally. This creates no remote connection and does not
expose Dera1.4 outside `127.0.0.1`.

## Task history

```powershell
python main.py tasks --json
python main.py task "TASK_ID" --json
python main.py continue-task "TASK_ID" "Show me the Downloads evidence." --json
```

Follow-ups are stored in the task's local activity history with their validated intent.
