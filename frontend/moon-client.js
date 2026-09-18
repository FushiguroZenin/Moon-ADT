/*
 * The UI talks only to this boundary. In local mode it uses the same-origin
 * Dera1.4 runtime; a future paired web client can provide MOON_API_BASE and
 * replace the transport without changing screens or components.
 */
class MoonClient {
  constructor(baseUrl = window.MOON_API_BASE || window.MOON_WEB_CONFIG?.apiBaseUrl || "") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.nativeFetch = window.fetch.bind(window);
  }

  url(path) {
    if (typeof path === "string" && /^https?:\/\//i.test(path)) return path;
    return `${this.baseUrl}${path}`;
  }

  async fetch(path, options = {}) {
    return this.nativeFetch(this.url(path), options);
  }

  async request(path, options = {}) {
    const response = await this.fetch(path, options);
    let payload = null;
    try { payload = await response.json(); } catch (_) { /* handled below */ }
    if (!response.ok) {
      throw new Error(payload?.detail || "Moon's local runtime could not complete that request.");
    }
    return payload;
  }

  get(path) { return this.request(path); }

  post(path, body) {
    return this.request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }
}

window.moonClient = new MoonClient();
// Existing screens can keep using fetch while all runtime traffic passes through
// MoonClient. A paired web build changes MOON_API_BASE, not the UI calls.
window.fetch = (path, options) => window.moonClient.fetch(path, options);
