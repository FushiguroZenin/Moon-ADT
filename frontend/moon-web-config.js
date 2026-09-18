/*
 * Moon web deployment configuration.
 *
 * This file is deliberately safe to publish: it contains no device token,
 * pairing code, or local path. A deployed Moon site remains in its paired
 * connection state until a future authenticated relay supplies an API base.
 *
 * Keep apiBaseUrl blank for the public site. Do not point it at a computer's
 * local IP address or expose the local Dera1.4 API to the internet.
 */
window.MOON_WEB_CONFIG = {
  mode: ["127.0.0.1", "localhost"].includes(window.location.hostname) ? "local" : "paired-web",
  apiBaseUrl: "",
  relayBaseUrl: "",
  connectionLabel: "Awaiting a paired Moon runtime",
};
