#!/usr/bin/env python3
"""
Tiny HTTP JSON wrapper around chat.py for in-cluster deployment.

Endpoints:
  GET     /healthz              -> 200 ok
  GET     /info                 -> backend info (URL + model, no key)
  POST    /chat                 -> {"model": "...", "reply": "..."}
  OPTIONS /chat, /info, /healthz -> CORS preflight when enabled

Reads the same three env vars as chat.py:
  OPENAI_DEFAULT_URL
  OPENAI_DEFAULT_APIKEY
  OPENAI_DEFAULT_MODELNAME
Optional:
  OPENAI_INSECURE_TLS=1   skip TLS verify (RHDP self-signed cert)
  PORT                    default 8080
  CORS_ALLOW_ORIGIN       comma-separated browser origins for the Next.js UI,
                          or "*" for demo-only permissive CORS
  FRONTEND_ORIGIN         fallback single-origin alias for CORS_ALLOW_ORIGIN
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

DEFAULT_PROMPT = "Say hello."
MAX_REQUEST_BYTES = 64 * 1024


def upstream_chat(prompt: str) -> dict:
    base = os.environ["OPENAI_DEFAULT_URL"].rstrip("/")
    key = os.environ["OPENAI_DEFAULT_APIKEY"]
    model = os.environ["OPENAI_DEFAULT_MODELNAME"]
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 256,
        "temperature": 0.2,
    }).encode("utf-8")
    req = urllib.request.Request(
        base + "/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    ctx = ssl.create_default_context()
    if os.environ.get("OPENAI_INSECURE_TLS") == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cors_origin_for(request_origin: str | None) -> str | None:
    configured = os.environ.get("CORS_ALLOW_ORIGIN") or os.environ.get("FRONTEND_ORIGIN")
    if not configured:
        return None
    if configured.strip() == "*":
        return "*"
    if not request_origin:
        return None
    allowed = {origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()}
    normalized_request = request_origin.rstrip("/")
    if normalized_request in allowed:
        return request_origin
    return None


def route_path(raw_path: str) -> str:
    return urlparse(raw_path).path


class Handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        allowed_origin = cors_origin_for(self.headers.get("Origin"))
        if not allowed_origin:
            return
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "600")
        if allowed_origin != "*":
            self.send_header("Vary", "Origin")

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _empty(self, code):
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self._send_cors_headers()
        self.end_headers()

    def log_message(self, fmt, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _html(self, code, body):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self._send_cors_headers()
        self.end_headers()

    def do_OPTIONS(self):
        path = route_path(self.path)
        if path in {"/", "/healthz", "/info", "/chat"}:
            return self._empty(204)
        return self._json(404, {"error": "not found"})

    def do_GET(self):
        path = route_path(self.path)
        if path == "/healthz":
            return self._json(200, {"ok": True})
        if path == "/info":
            return self._json(200, {
                "backend_url": os.environ.get("OPENAI_DEFAULT_URL"),
                "model": os.environ.get("OPENAI_DEFAULT_MODELNAME"),
                "chat_endpoint": "/chat",
                "cors_enabled": bool(os.environ.get("CORS_ALLOW_ORIGIN") or os.environ.get("FRONTEND_ORIGIN")),
            })
        if path == "/":
            return self._html(200, INDEX_HTML)
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if route_path(self.path) != "/chat":
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BYTES:
            return self._json(413, {"error": "request too large"})
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "invalid json"})
        prompt = req.get("prompt") or DEFAULT_PROMPT
        if not isinstance(prompt, str):
            return self._json(400, {"error": "prompt must be a string"})
        try:
            up = upstream_chat(prompt)
        except urllib.error.HTTPError as e:
            return self._json(e.code, {
                "error": "upstream",
                "detail": e.read().decode("utf-8", "replace")[:MAX_ERROR_DETAIL],
            })
        except Exception as e:
            return self._json(502, {"error": type(e).__name__, "detail": str(e)[:300]})
        reply = up["choices"][0]["message"]["content"].strip()
        return self._json(200, {"model": up.get("model"), "reply": reply})


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sample chat — Austin RHUG 2026</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 16px/1.5 system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; }
  h1 { margin: 0 0 .25rem; }
  .meta { font-size: 13px; opacity: .75; margin-bottom: 1.5rem; }
  textarea { width: 100%; min-height: 90px; padding: .6rem; font: inherit; box-sizing: border-box; }
  button { font: inherit; padding: .55rem 1rem; cursor: pointer; }
  button[disabled] { opacity: .55; cursor: progress; }
  pre { white-space: pre-wrap; background: rgba(127,127,127,.12); padding: 1rem; border-radius: 6px; }
  .row { display: flex; gap: .5rem; align-items: center; margin: .5rem 0 1rem; }
  .pill { display: inline-block; padding: .15rem .5rem; border-radius: 999px;
          background: rgba(127,127,127,.18); font-size: 12px; }
</style>
</head>
<body>
  <h1>Sample chat backend</h1>
  <p class="meta">The production UI is served by the separate Next.js frontend. This lightweight page remains for direct backend smoke tests.</p>
  <div class="meta">
    backend: <span class="pill" id="backend">…</span>
    model: <span class="pill" id="model">…</span>
  </div>
  <textarea id="prompt" placeholder="Ask something…">In one sentence, what is Red Hat OpenShift AI?</textarea>
  <div class="row">
    <button id="send">Send</button>
    <span id="status"></span>
  </div>
  <pre id="reply">(reply will appear here)</pre>
<script>
async function loadInfo() {
  try {
    const r = await fetch('/info'); const j = await r.json();
    document.getElementById('backend').textContent = j.backend_url || '?';
    document.getElementById('model').textContent = j.model || '?';
  } catch (e) { /* ignore */ }
}
async function send() {
  const btn = document.getElementById('send');
  const status = document.getElementById('status');
  const out = document.getElementById('reply');
  const prompt = document.getElementById('prompt').value.trim();
  if (!prompt) return;
  btn.disabled = true; status.textContent = 'thinking…'; out.textContent = '';
  const t0 = performance.now();
  try {
    const r = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({prompt})
    });
    const j = await r.json();
    const ms = Math.round(performance.now() - t0);
    if (!r.ok) { out.textContent = 'ERROR ' + r.status + ': ' + (j.detail || j.error); }
    else { out.textContent = j.reply; status.textContent = j.model + ' · ' + ms + ' ms'; }
  } catch (e) { out.textContent = 'fetch failed: ' + e; }
  finally { btn.disabled = false; }
}
document.getElementById('send').addEventListener('click', send);
document.getElementById('prompt').addEventListener('keydown', e => { if (e.metaKey && e.key === 'Enter') send(); });
loadInfo();
</script>
</body>
</html>
"""


def main():
    port = int(os.environ.get("PORT", "8080"))
    backend = os.environ.get("OPENAI_DEFAULT_URL")
    model = os.environ.get("OPENAI_DEFAULT_MODELNAME")
    print(f"listening on :{port} backend={backend} model={model}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
