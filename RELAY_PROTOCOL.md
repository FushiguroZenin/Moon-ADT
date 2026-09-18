# Moon outbound relay foundation

`run_relay.py` starts a separate FastAPI relay for local development on
`127.0.0.1:8787`. It has no computer-control authority.

The relay accepts device registration, stores signed outbound events, and exposes a
per-device command queue. It only accepts the current read-only Dera1.4 command
allow-list. The local runtime must validate a queued request before it does any work;
the relay cannot approve or execute a file operation.

The production relay must run behind HTTPS and replace the development registration
endpoint with device-first pairing-code enrollment and durable device-token handling.
Moon's local runtime will not enable an outbound relay URL unless it uses HTTPS.
# Device-first browser pairing

Moon does not require an account for initial device pairing. A user generates a
one-time code on the PC from Dera1.4. When outbound relay is enabled, the local
runtime publishes only the SHA-256 hash of that code and its expiry to the relay.
The raw code remains on the PC screen and in the user's browser entry.

The browser sends the code to `POST /v1/browser-pairing/complete`. The relay
exchanges it for an opaque browser session tied to one Moon device. It does not
receive the local runtime bearer token, a local API address, file paths, or
system evidence. The paired PC can list and revoke browser sessions using its
own relay credential through the local API.

Browser pairing is identity setup only. It does not grant computer-control
authority. A future relay command endpoint must validate the browser session,
use a Dera1.4 allow-list, and preserve proposal → approval → execution →
verification on the PC.

## Browser read-only requests

A paired browser can now call `POST /v1/browser/commands` with one of the
same read-only Dera1.4 request types: system status, slow-computer
investigation, Downloads inspection, startup diagnosis, or application-crash
investigation. The relay authenticates the browser session, derives the device
from that session, and records the session hash against the queued command.

Dera1.4 picks the command up through its existing outbound poll and posts its
result through the device-authenticated event channel. The relay stores that
result separately and returns it only from
`GET /v1/browser/commands/{command_id}` to the browser session that created
the request. File actions, proposal approval, execution, replacement, and
deletion are not accepted on this browser endpoint.

When deployed, `MOON_WEB_ORIGIN` must contain the exact HTTPS Moon web origin.
CORS is disabled unless this variable is set, and the relay never uses a wildcard
browser origin.

## Paired web conversation

`POST /v1/browser/questions` accepts ordinary browser text and maps it only to
the read-only allow-list. The relay uses conservative deterministic intent rules
and returns a focused capability message when it cannot identify a safe
investigation. It does not call a language model or execute tools.

For a slow-computer investigation, Dera1.4 runs the task locally and asks the
local Llama model for a grounded explanation of that task's findings. The
browser receives the validated explanation and evidence cards through the same
session-owned command result. Other supported requests return the existing
read-only Dera1.4 evidence. Browser chat never reaches proposal or file-action
endpoints.
