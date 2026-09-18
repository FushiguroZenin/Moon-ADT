/*
 * Moon web deployment configuration.
 *
 * This file is deliberately safe to publish: it contains no device token,
 * pairing code, or local path. A deployed Moon site remains in its paired
 * connection state until a future authenticated relay supplies an API base.
 *
 * Keep apiBaseUrl blank for the public site. relayBaseUrl may contain the
 * public relay address, but never a computer's local IP or API address.
 */
window.MOON_WEB_CONFIG = {
  mode: ["127.0.0.1", "localhost"].includes(window.location.hostname) ? "local" : "paired-web",
  apiBaseUrl: "",
  relayBaseUrl: "https://moon-relay.onrender.com",
  connectionLabel: "Awaiting a paired Moon runtime",
};
