/**
 * api.js — All fetch calls to the Flask backend
 */

const API_BASE = window.location.origin;

const Api = {

  /** Upload a file and get schema back */
  async upload(file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");
    return data;
  },

  /** Run a natural-language query */
  async query(question, dbPath, schema) {
    const res = await fetch(`${API_BASE}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, db_path: dbPath, schema })
    });
    const data = await res.json();
    if (!res.ok) throw Object.assign(new Error(data.error || "Query failed"), { data });
    return data;
  },

  /** Get query suggestions for a schema */
  async suggestions(schema) {
    const res = await fetch(`${API_BASE}/api/suggestions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ schema })
    });
    const data = await res.json();
    if (!res.ok) throw new Error("Suggestions failed");
    return data.suggestions || [];
  },

  /** Health check */
  async health() {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.json();
  }
};
