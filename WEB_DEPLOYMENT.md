# Moon web shell

This repository can deploy `frontend/` as a static Vercel site using
`vercel.json`. The deployed site uses the same Moon dashboard, documentation,
permissions, and visual language as the local interface.

## What a deployment does

A Vercel deployment hosts the Moon web shell. It does **not** host Dera1.4,
Ollama, the user's files, or a local computer API. With the default
`frontend/moon-web-config.js`, the dashboard shows an awaiting-pairing state.

## Safe connection design

1. The user installs and starts Dera1.4 on their own computer.
2. Dera1.4 makes an outbound authenticated connection to Moon's relay.
3. The browser exchanges a PC-generated one-time pairing code for its own
   opaque session, stored only in that browser session.
4. The relay forwards only allow-listed requests to the local runtime.
5. Dera1.4 validates every request and retains the existing proposal,
   approval, execution, and verification boundary.

The web site must never be configured to call `127.0.0.1`, a private LAN
address, or an unauthenticated Dera1.4 API. A browser cannot safely turn a
Vercel page into a general computer-control channel.

## Deploying the shell

1. Create the GitHub repository when ready and push this project.
2. Import it into Vercel.
3. Leave the framework preset as **Other**. The included `vercel.json` serves
   `frontend/` as the deployment output.
4. Deploy. The page will work as a public Moon information and pairing shell,
   while showing that it is awaiting a paired runtime.

## Connecting it later

Do not put a secret in `moon-web-config.js`. The production web client uses a
device-first pairing code and receives an opaque browser session after pairing
with a PC. That session, not a static API URL or device token, authorizes the
read-only relay requests. The relay is still a deployment foundation and must
be hosted with persistent storage and HTTPS.

For the device-first pairing and read-only browser endpoints, deploy the relay
behind HTTPS and set its `MOON_WEB_ORIGIN` environment variable to the exact
Moon web origin, for example `https://moon.example.com`. This enables browser
requests only from that web application; do not use a wildcard origin.

See `DEPLOYMENT_CHECKLIST.md` for the complete relay, Vercel, pairing, and
verification sequence.
