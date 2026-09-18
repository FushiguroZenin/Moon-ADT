# Moon end-to-end deployment checklist

Moon is split deliberately:

- **Vercel:** the static Moon web interface in `frontend/`.
- **Relay container:** the persistent HTTPS service that holds device tokens,
  pairing-code hashes, browser sessions, and read-only command results.
- **User PC:** the local Dera1.4 runtime and Ollama model. It makes outbound
  HTTPS requests; it never accepts an inbound web connection.

## 1. Deploy the relay

Use a container host with a persistent volume and HTTPS, such as a managed
container platform or a small server behind a TLS proxy. Build with
`Dockerfile.relay` and mount `/var/lib/moon` persistently.

Set these environment values:

```text
MOON_WEB_ORIGIN=https://your-moon-domain.example
MOON_RELAY_DATABASE=/var/lib/moon/moon-relay.db
```

Do not expose port 8787 directly to the internet without an HTTPS proxy. The
public relay URL must begin with `https://`.

## 2. Deploy Moon web to Vercel

Import the repository into Vercel. `vercel.json` serves the existing
`frontend/` directory. Before deploying, set the safe public relay address in
`frontend/moon-web-config.js`:

```js
relayBaseUrl: "https://relay.your-moon-domain.example",
```

This is a public address, not a secret. Do not add a device token, local IP,
or localhost address to the web configuration.

## 3. Connect the PC

On the PC running Dera1.4, set the same HTTPS relay URL in Moon Settings,
enable the outbound relay, and restart the local runtime. The first heartbeat
enrols the random Moon device ID and retains its device token locally.

## 4. Pair and verify

1. Generate a pairing code from the local Moon Settings page.
2. Open the Vercel Moon site on a browser or phone.
3. Enter the code in **Pair this device**. The browser receives an opaque
   session token; it never receives the PC's relay credential.
4. Wait for the paired PC to poll the relay.
5. Confirm that Storage, Memory, and Processor cards show real PC values.
6. Ask: “Why is my PC slow?” and confirm Moon returns evidence from the PC.
7. Revoke the browser session locally and confirm the web client can no longer
   retrieve data.

## Expected offline behavior

If the PC, local runtime, or outbound relay is not running, the web interface
must show a waiting or unavailable state. It must never reuse an old snapshot
as if it were current and must not offer file-changing controls.
