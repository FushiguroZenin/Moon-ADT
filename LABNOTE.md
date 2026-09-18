# Moon — Development Lab Note

## What Moon is

Moon is a personal AI computer agent. It is intended to understand what is happening
on a user's computer, investigate problems, explain evidence, propose safe actions,
carry out only approved actions, and verify the result.

Moon is the application and user-facing identity. **Dera1.4** is the technical name
for Moon's local controlled-agent runtime.

Dera1.4 separates responsibilities deliberately:

```text
Python / Dera1.4: observe, calculate, validate, enforce permissions, act, verify
Llama 3.1 8B: interpret evidence and communicate naturally
Moon: the product experience
```

The model is not trusted to measure the computer, invent facts, approve itself, or
perform arbitrary commands. Python is the source of factual system state.

## Core operating loop

```text
Understand → Observe → Reason → Propose → Permission → Execute → Observe → Verify
```

The current implementation is terminal-first. A polished interface and computer UI
control are future phases, not present features.

## What has been built

### 1. Dera1.4 foundation

- Python project structure under `dera/`
- Terminal command interface in `main.py`
- Structured findings and explicit tool-registry foundation
- Local SQLite activity store at `data/moon.db`

### 2. Read-only computer observation

Moon can collect structured data for:

- Windows version and hostname
- CPU use and logical core count
- RAM capacity, use, and available memory
- C: drive capacity, use, and free space
- Network-interface availability
- Uptime and boot time
- Running processes, memory use, sampled CPU use, state, and start time

The process CPU sampler was corrected to take two readings over a short interval.

### 3. Diagnostics and investigation

The command below creates a recorded task, gathers system facts, runs performance
rules, conditionally investigates storage, and returns findings plus a next step:

```powershell
python main.py investigate slow-computer --json
```

The deterministic diagnostics identify high CPU, high memory use, nearly full
storage, and the largest measured memory consumer.

### 4. Storage inspection

Moon can safely inspect user-owned folders and reports:

- Largest files
- Largest top-level subfolders
- Largest file types
- Total size and unreadable-item count

The inspection boundary is the current user's home directory. System-wide paths are
rejected.

```powershell
python main.py inspect "C:\Users\Indra\Downloads" --json
```

### 5. Proposals, approval, and controlled moves

Moon can generate reviewable cleanup proposals from Downloads. A proposal includes
the exact path, estimated affected size, reason, risk level, and approval requirement.

Current action policy:

- Proposals do not change files.
- Preview validates a proposed move without changing files.
- Approval is proposal-specific and stored locally.
- Execution can only move one approved folder to an existing user-selected directory.
- Source and destination must be inside the current user's home directory.
- The executor verifies source disappearance and destination existence afterward.
- Permanent deletion is neither implemented nor proposed.
- A user can dismiss an unacted proposal without affecting the underlying folder.

Relevant commands:

```powershell
python main.py propose cleanup-downloads --json
python main.py preview "PROPOSAL_ID" "C:\Users\Indra\Documents\Archived Downloads" --json
python main.py approve "PROPOSAL_ID" "C:\Users\Indra\Documents\Archived Downloads" --json
python main.py execute "PROPOSAL_ID" --json
python main.py dismiss "PROPOSAL_ID" --json
```

`execute` is intentionally separate from preview and approval.

### 6. Local 8B reasoning

Moon now uses a replaceable `ModelProvider` interface, with Ollama as the first local
runtime and `llama3.1:8b` as the default configured model.

```powershell
python main.py explain-slow --json
```

The model receives a fresh, read-only investigation and provides an interpretation.
It has no direct filesystem access, tool execution path, permission control, or
ability to approve actions.

### 7. Grounded model output

The first free-form 8B explanation invented an incorrect total disk capacity. This
validated the core Dera1.4 principle: model prose must not be treated as system fact.

Moon now requires the model to return structured JSON containing only:

- A short interpretation without numbers
- IDs of relevant Dera1.4 findings
- A next step without numbers

Dera1.4 validates the IDs, rejects numeric claims, and renders all measurements from
Python's evidence. Invalid or ungrounded model output falls back to a deterministic
response. `--debug` exposes the local raw response and validation reason for tuning.

```powershell
python main.py explain-slow --json --debug
```

## Live findings recorded during development

The initial slow-computer investigation found:

- C: drive near full, reaching roughly 94–95% usage.
- Downloads consuming about 254 GB.
- Large downloaded game/archive folders as the principal storage consumers.
- Memory use increasing while the 8B model is active.
- `llama-server.exe` using about 4.95 GB of RAM during an active model run.

This makes the 8B model suitable for active investigation and explanation, but not a
good candidate to remain loaded continuously on this 16 GB computer.

## Current limitations

- Terminal interface only
- One investigation workflow: slow computer
- Read-only diagnostics are broader than action capabilities
- One controlled action: moving an approved folder
- No permanent deletion capability
- No visual screen control
- No proactive monitoring
- No long-lived conversational task manager

## Recent additions

### Persistent tasks and follow-ups

Tasks are now stored in SQLite and can be listed, retrieved, and extended with a
follow-up. A follow-up is classified through the same allow-listed router, then the
matching read-only workflow runs and its resulting evidence is attached to the
original task's activity history.

```powershell
python main.py tasks --json
python main.py task "TASK_ID" --json
python main.py continue-task "TASK_ID" "Show me the Downloads evidence." --json
```

This provides the first persistent-agent behavior: Moon can begin an investigation,
receive a later question, and add fresh evidence without losing the earlier context.

### Startup and installed-application diagnostics

Moon now reads current-user and all-users Windows Run registry locations, the current
user Startup folder, and Windows uninstall registry entries. The startup collector
filters `desktop.ini`, which is a folder-configuration file rather than an executable
startup item.

```powershell
python main.py diagnose applications --json
python main.py inspect-startup "ENTRY_NAME" --json
python main.py propose startup --json
```

Startup proposals are review-only. Moon currently cannot disable startup entries,
change the registry, or uninstall applications.

### Crash investigation

Moon can create a read-only task for an application crash investigation:

```powershell
python main.py investigate crash chrome.exe --json
```

The dedicated observer invokes the fixed Windows `wevtutil` program without a shell,
accepts only a validated application name, reads recent Application events 1000 and
1001, and extracts timestamps, faulting application names, and faulting modules.
No repair action is proposed or performed.

### Hardware and connectivity

Moon now has a read-only hardware diagnostic:

```powershell
python main.py diagnose hardware --json
```

It reports battery charge and power status when Windows exposes it, active network
interfaces and traffic counters, and NVIDIA GPU telemetry through `nvidia-smi` when
available. Missing metrics are explicitly reported as unavailable.

### Proactive monitoring

Moon can establish and compare local monitoring snapshots:

```powershell
python main.py monitor check
```

Snapshots store free C: storage, memory percentage, and startup-entry names. A later
check reports a storage decrease of at least 5 GB, new startup entries, or memory use
at or above 85%. Monitoring is local, quiet, and read-only; it does not run as a
background scheduler or send notifications yet.

### Human-readable terminal reports

Moon now renders concise reports by default for task history, task findings,
slow-computer investigations, grounded model explanations, proposals, and verified
moves. `--json` remains available for complete structured output, debugging, and API
consumers.

### Test suite and packaging

A pytest suite now covers deterministic intent routing, grounded-model validation and
fallback behavior, task persistence, and proposal dismissal. The project declares a
`test` optional dependency and restricts setuptools discovery to `dera*`, preventing
the runtime `data/` directory from being packaged accidentally.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests have been run successfully in the project's virtual environment.

### Local Dera1.4 API

Moon now exposes a localhost-only FastAPI service for a future user interface:

```powershell
python -m pip install -e .[api]
python run_api.py
```

The service binds to `http://127.0.0.1:8765` and provides local endpoints for system
status, slow-computer tasks, task history, monitor checks, Downloads inspection,
proposal review, and proposal preview. Local interactive documentation is available
at `/docs`.

The API does not expose approval or execution endpoints. That prevents an eventual
web client from gaining computer-control authority before the complete permission and
pairing design is ready.

### Device pairing foundation

The local API now has a pairing foundation for the future Vercel-hosted Moon client:

- A persistent local device ID
- Short-lived one-time pairing codes, valid for ten minutes
- One-time device tokens, stored locally only as SHA-256 hashes
- Paired-client metadata
- A local pairing audit trail

These endpoints are still localhost-only and create no remote connection, tunnel, or
cloud account. The future pairing transport must use an outbound authenticated channel
from the local runtime; a public web app must never directly receive broad system
access to a user's computer.

## Eventual web architecture

```text
Moon web app on Vercel
        ↕ authenticated pairing and outbound connection
Moon local runtime on the user's computer
        ↕
Dera1.4 diagnostics, tasks, permissions, proposals, execution, verification
        ↕
Windows system
```

The web app will provide the conversation, dashboard, task timeline, and approval
experience. Dera1.4 remains the local trusted control plane and the only component
that can observe or operate the computer.

## Next milestones

1. Add a conversational task router that maps natural requests to allowed Dera1.4
   investigations without granting arbitrary tool access. *(Completed for the first
   safe intents.)*
2. Add a background scheduler for proactive local monitoring, with conservative
   notification policies.
3. Add secure outbound pairing transport and web-request authentication before any
   Vercel interface connects to a local runtime.
4. Build the Moon web dashboard and conversation client against the local API.
5. Add project troubleshooting, battery/power expansion, and broader GPU/network
   diagnostics.
6. Add further controlled actions only with proposal, approval, validation, and
   post-action verification.

## Dashboard and conversation client

Moon now has a local browser dashboard served from the Dera1.4 FastAPI runtime at
`/app`. It is a conversation-first interface rather than a generic system-monitoring
screen. The layout includes:

- A quiet local-runtime indicator and system overview
- Live CPU, memory, storage, and connectivity values from `GET /status`
- Evidence cards that open a detail panel for the selected metric
- A clear permission boundary that explains what Moon may observe and what requires
  an explicit user approval
- A footer linking the future GitHub, documentation, and permissions areas

The dashboard uses the browser's local clock for its morning, afternoon, or evening
greeting. It does not assume a user name and does not include an account system.

The metric detail panel only describes values returned by the current local snapshot.
Its recommendations are deterministic and conservative: for example, high storage
usage suggests inspecting large user-accessible folders; it does not claim a root
cause or suggest deleting, moving, closing, or changing anything automatically.

### Local conversation flow

The large center panel is now a live conversation thread. A user can type a request
such as:

```text
Why is my computer slow?
```

The frontend sends the request to the local-only `POST /ask` endpoint. That endpoint
uses `IntentRouter` to select from Dera1.4's limited safe task allow-list. The current
allow-list supports:

- System status
- Slow-computer investigation
- Downloads inspection
- Downloads cleanup-proposal review

The slow-computer route runs the existing read-only investigation, then returns the
task, deterministic findings, and recommended next step to the conversation. The UI
renders the user's message, a temporary investigation state, Moon's response, and
clickable finding labels. Those labels are evidence references, not permission to
take action.

Unrecognised requests receive a bounded explanation of Moon's current capabilities.
The `/ask` endpoint does not approve, execute, delete, move, close, or alter anything.
Cleanup proposals remain unapproved and execution stays disabled through this UI.

### Running the updated interface

Restart the local server after changes to the API, then open the dashboard:

```powershell
python run_api.py
```

Open `http://127.0.0.1:8765/app/` and refresh the page. The dashboard refreshes its
status snapshot every fifteen seconds; the **Refresh analysis** control requests a
fresh snapshot immediately.

### Task-aware local chat

The dashboard input opens a centered Moon chat card. The dashboard itself remains a
stable system overview. The chat card can be minimized without losing the current
thread, while closing it or refreshing the browser starts a new local conversation.

The first supported investigation establishes an active task for that local chat
session. Later messages are sent to `POST /tasks/{task_id}/follow-up`, recorded in
the task's activity history, and limited to the same read-only allow-list. This lets
Moon handle evidence follow-ups such as asking for Downloads details after a
slow-computer investigation.

The local Llama 3.1 8B model now has a grounded conversation role for slow-computer
investigations. Dera1.4 runs the investigation first; the model receives only the
user request and returned findings. Its response must be JSON, may select only
returned finding IDs, and may not introduce numerical claims. Invalid model output
or an unavailable Ollama runtime falls back to Dera1.4's deterministic response.

Chat finding labels render readable English rather than raw JSON. Moon responses can
also include **Details** and **Recommended next step** cards. Any suggested change
states that explicit permission is required before Moon can carry it out.

When a Downloads review returns move proposals, the chat renders review-only cards.
They show the proposed item and estimated effect, but do not move or delete files.

### Guided move permission flow

Downloads move proposals can now be reviewed in a local guided flow. The required
stages are visible and separate:

```text
Proposed → Previewed → Approved → Executed and verified
```

The user supplies an existing destination folder. **Preview** performs a dry run and
validates the source, destination, home-directory boundary, and target conflict; it
does not move files. **Approve** repeats validation and records explicit local
approval for that exact proposal and destination. **Execute and verify** is a final,
separate user action that performs the already-approved move and verifies that the
source disappeared and the destination exists.

The local API exposes these endpoints only on `127.0.0.1`:

- `POST /proposals/{proposal_id}/preview`
- `POST /proposals/{proposal_id}/approve`
- `POST /proposals/{proposal_id}/execute`

No API call is made merely by viewing a proposal. This local UI flow is not yet
available to a future remote or Vercel client; remote approval requires the planned
pairing and authenticated transport design.

### Controlled copy

Moon now supports **copy** as a separate controlled action for an existing proposal.
Copy preserves the original source. Its dry-run validation confirms the same
user-home boundary, source existence, destination directory, name-conflict rule, and
also checks that the destination has enough free space. Execution copies the item and
verifies that the target exists with the same calculated size as the source.

The proposal UI lets the user select **Move** or **Copy** before previewing. The
stages remain separate for both actions: proposed, previewed, approved, then executed
and verified. Copy does not provide overwrite or replace behavior; an existing target
name is a validation error. Delete and replace are still not implemented.

### Local monitoring controls

Settings now includes a manual **Check now** control for local monitoring. A check
stores a snapshot and reports only meaningful changes: a large free-storage drop,
new startup entries, or high current memory use. Monitoring remains read-only, has no
background scheduler, and sends no notifications. Recent monitor snapshots are
available through the local `GET /monitor/history` endpoint; `GET /monitor/check`
runs a new check.

Background monitoring is opt-in and disabled by default. While the local Moon runtime
is running, users can enable checks at a conservative interval between five minutes
and twenty-four hours. Meaningful findings are saved locally as monitor events and
shown in the Activity view. The scheduler stops with the local runtime and does not
create a Windows scheduled task, send external notifications, or take any action.

### Application crash investigation

Moon chat can now recognise crash language such as “Chrome keeps crashing” or “Why
did Discord close unexpectedly?” It extracts a simple application name, reads recent
Windows Application event reports through the existing read-only Dera1.4 crash task,
and records the result as a task. If an application name is missing, Moon asks for it
and treats the next short reply as the app name. It does not repair, restart, update,
or change applications from this investigation.

### Pairing controls

Settings now exposes the existing localhost-only pairing foundation. A user can
generate a single-use code that expires after ten minutes and complete pairing with a
named client. The local runtime records paired-client metadata and keeps only hashed
device tokens. The Settings page never displays a token after pairing.

This is a local pairing demonstration only. It creates no cloud account, public
endpoint, tunnel, remote observation channel, or remote computer-control path. A
future Vercel client must use the planned authenticated outbound connection from the
local runtime.

### Portable frontend transport

The existing local frontend now loads `frontend/moon-client.js`. `MoonClient` is the
single transport boundary for UI API traffic. In local mode it preserves the current
same-origin calls to Dera1.4. A future web host can provide `window.MOON_API_BASE` to
route the exact same screens through a paired authenticated relay, without rewriting
the dashboard, chat, Activity, System, Settings, or permission UI.

### Vercel-ready Moon web shell

The same interface can now be deployed as a static web shell through
`vercel.json`, with `frontend/` as its output directory. The page loads a
safe, publishable `moon-web-config.js`. Its default configuration is
`paired-web` with no API URL, so the dashboard explicitly shows an
**Awaiting pairing** state instead of attempting to observe a computer from a
website.

This is deliberate: Vercel hosts the Moon interface and public documentation;
it does not host Dera1.4, Ollama, local files, or an open computer-control
port. The future production path remains user sign-in and device selection,
then an authenticated outbound relay from the local runtime. `WEB_DEPLOYMENT.md`
documents the boundaries and deployment steps. No secret, pairing token, LAN
address, or localhost URL belongs in the deployed web configuration.

### Responsive and mobile companion experience

Moon's dashboard now has a responsive layout for tablets and phones. Navigation,
system evidence, settings, public documentation, permission flow, and controlled
action dialogs reflow for touch-sized screens; inputs and action buttons have
larger usable targets. The local app retains the full desktop experience.

On a deployed Moon web shell with no paired runtime, phone visitors see a
companion-specific state rather than empty or fabricated system data. It explains
that the PC runs Dera1.4, while the phone is for reviewing a paired device,
activity, permissions, and future conversations. The mobile Ask Moon control is
hidden until a real authenticated paired transport exists. This prevents a web
visitor from believing that Moon is reading their phone or PC without a pairing.

### Device-first browser pairing

Moon now has a no-account browser-pairing foundation. A pairing code is generated
on the PC and remains local. If the user has enabled an HTTPS outbound relay,
Dera1.4 sends the relay only an active code hash and its expiry. A browser can
exchange the code for an opaque, device-scoped browser session. The session is
stored in browser session storage and is invalidated when the PC revokes it.

The relay has endpoints for the local runtime to publish code hashes, list paired
browsers, and revoke one. It has a browser endpoint for exchanging a code and a
session-status endpoint. The Vercel interface now includes a Pair this device form
when operating as the web shell. It remains unavailable until a production relay
URL is configured, and pairing alone does not provide computer-control access.

### Paired web read-only evidence

The paired web shell can now request a current system snapshot from its own
paired PC. It authenticates with the browser session, queues a
`system_status` command, waits for Dera1.4's outbound polling loop, then
renders the returned snapshot in the same Storage, Memory, and Processor cards
used by the local dashboard. If the PC is offline, Moon reports that it is
waiting for the paired runtime rather than presenting stale or fabricated data.

The relay associates every browser-originated command with the hash of the
creating browser session, records the result after the local runtime returns
it, and exposes it only to that same session. The browser command allow-list
contains only system status, slow-computer investigation, Downloads inspection,
startup diagnosis, and application-crash investigation. No browser endpoint can
create a file-action proposal, approve one, execute one, replace files, or
delete files.

### Paired web conversation

The paired web dashboard can now use its existing Moon chat modal after a live
PC connection is established. Browser text goes to a relay-side deterministic
intent mapper, which only accepts the existing read-only capabilities. The relay
queues the matching request with the original question, Dera1.4 performs the
investigation locally, and the session-owning browser receives the result.

Slow-computer questions additionally use the local grounded Llama conversation
layer after Dera1.4 has collected the evidence. The web chat renders the same
plain-English evidence, Details, and Recommended next step cards as the local
interface. Unknown questions receive a concise prompt describing supported
investigations. No paired-web chat route can make a file proposal or initiate a
computer-changing action.

### Deployable relay package

The relay now has `Dockerfile.relay`, `docker-compose.relay.yml`, a scoped
`.env.relay.example`, and `DEPLOYMENT_CHECKLIST.md`. It runs as an unprivileged
container user and persists its SQLite database under `/var/lib/moon`; a named
volume keeps device credentials, paired browser sessions, and read-only command
results through restarts. The relay must be placed behind HTTPS and configured
with the exact Moon Vercel origin through `MOON_WEB_ORIGIN`.

Device registration no longer replaces an existing relay credential. A device
ID can enroll once, and later browser access uses the short-lived pairing-code
flow. This avoids a known device ID being used to silently replace the PC's
outbound relay token.

### Windows local-runtime installer foundation

Moon now has a user-level Windows packaging path. `moon_runtime.py` launches
the localhost-only Dera1.4 API and opens a first-run setup page unless started
with `--background`. The bundled API resolves frontend assets correctly in a
PyInstaller executable through `_MEIPASS` while retaining normal source-mode
paths during development.

`installer/build-runtime.ps1` produces `MoonRuntime.exe` with frontend assets;
`installer/moon.iss` creates a low-privilege Inno Setup installer that places
the runtime under Local AppData and registers a per-user startup entry. The
first-run page gives users a diagnostics-only option and describes Ollama as an
optional local-AI install. `INSTALLER_GUIDE.md` records the build and release
requirements. This is packaging infrastructure; an installer has not been
compiled or signed yet.

### Installed runtime hardening and V1 guidance boundary

Packaged Moon now sets `MOON_DATA_DIR` to `%LOCALAPPDATA%\Moon\data` before it
starts Dera1.4. Task history, proposals, pairing state, monitoring state, and
relay configuration use a shared path helper, so they no longer depend on the
project directory or the working directory of a startup shortcut. Runtime logs
are written to `%LOCALAPPDATA%\Moon\logs\MoonRuntime.log`.

The installed runtime defaults to `MOON_GUIDANCE_ONLY=1`. Its server rejects
move and copy preview, approval, and execution endpoints, preserving V1 as a
diagnose-and-guide product for sensitive file tasks. The first-run screen now
calls `/runtime/health` to show runtime/Ollama status, offers a pairing-code
control, and distinguishes diagnostics-only operation from optional local AI.


### Local AI onboarding

The first-run page now presents local AI as a product choice rather than a model name or terminal command. **Enable local AI** opens a clear confirmation dialog: the model stays private on the PC, requires several GB of disk space, and uses additional RAM while active; it is recommended for natural conversation and clearer explanations. Diagnostics-only Moon remains usable without it.

After confirmation, Moon detects an existing Ollama installation. If Ollama is missing, it opens the official installer; once present, a second explicit action starts the recommended local model download with no shell command exposed to the user. The local API exposes read-only status and a user-confirmed model-download endpoint. Public documentation now includes this Ollama recommendation and its resource tradeoffs.

### Windows runtime tray controls

The packaged Windows runtime now uses a small system-tray companion rather than
being invisible after launch. It provides **Open Moon**, **Open setup**,
**Check runtime status**, and **Quit Moon** commands. The installer opens setup
after installation, while later launches open the dashboard; startup runs the
same runtime quietly with the tray icon available. `pystray` and Pillow are
bundled by the Windows packaging script for this purpose.

### Guided web pairing

First-run setup now has a guided **Set up pairing** dialog. The user enters only
the public HTTPS relay address, then Moon enables its outbound connection and
creates a short-lived code after that code hash is published successfully. The
dialog makes the network boundary explicit: no inbound PC connection, no relay
device token in the web page, and no pairing code shown until the relay confirms
it can receive it. Local Settings now lists paired web browsers and lets the PC
owner revoke each browser session.
