#!/usr/bin/env python3
"""
Tiny HTTP wrapper around chat.py for in-cluster deployment.

Endpoints:
  GET  /healthz                -> 200 ok
  GET  /                       -> backend info (URL + model, no key)
  POST /chat  body: {"prompt": "..."}  -> {"model": "...", "reply": "..."}

Reads the same three env vars as chat.py:
  OPENAI_DEFAULT_URL
  OPENAI_DEFAULT_APIKEY
  OPENAI_DEFAULT_MODELNAME
Optional:
  OPENAI_INSECURE_TLS=1   skip TLS verify (RHDP self-signed cert)
  PORT                    default 8080
"""
import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


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
        data=body, method="POST",
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


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _html(self, code, body):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/healthz":
            return self._json(200, {"ok": True})
        if self.path == "/info":
            return self._json(200, {
                "backend_url": os.environ.get("OPENAI_DEFAULT_URL"),
                "model": os.environ.get("OPENAI_DEFAULT_MODELNAME"),
            })
        if self.path == "/" or self.path.startswith("/?"):
            return self._html(200, INDEX_HTML)
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/chat":
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", "0"))
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "invalid json"})
        prompt = req.get("prompt") or "Say hello."
        try:
            up = upstream_chat(prompt)
        except urllib.error.HTTPError as e:
            return self._json(e.code, {"error": "upstream", "detail": e.read().decode("utf-8", "replace")[:600]})
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
  .pill { display: inline-block; padding: .15rem .5rem; border-radius: 999px; background: rgba(127,127,127,.18); font-size: 12px; }
</style>
</head>
<body>
  <h1>Sample chat</h1>
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
    const r = await fetch('/chat', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({prompt}) });
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
    print(f"listening on :{port} backend={os.environ.get('OPENAI_DEFAULT_URL')} model={os.environ.get('OPENAI_DEFAULT_MODELNAME')}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
