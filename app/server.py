#!/usr/bin/env python3
"""
Tiny HTTP JSON wrapper around chat.py for in-cluster deployment.

Endpoints:
  GET     /healthz              -> 200 ok
  GET     /info                 -> backend info (URL + model, no key)
  GET     /rag/info             -> chat + retrieval backend info (no key)
  POST    /chat                 -> {"model": "...", "reply": "..."}
  POST    /rag                  -> answer from supplied passages via embed/rerank/chat
  OPTIONS /chat, /rag, /rag/info, /info, /healthz -> CORS preflight when enabled

Reads the same three env vars as chat.py:
  OPENAI_DEFAULT_URL
  OPENAI_DEFAULT_APIKEY
  OPENAI_DEFAULT_MODELNAME
Retrieval env vars:
  EMBEDDINGS_URL
  EMBEDDINGS_MODEL
  RERANK_URL
  RERANK_MODEL
Optional:
  OPENAI_INSECURE_TLS=1   skip TLS verify (RHDP self-signed cert)
  PORT                    default 8080
  CORS_ALLOW_ORIGIN       comma-separated browser origins for the Next.js UI,
                          or "*" for demo-only permissive CORS
  FRONTEND_ORIGIN         fallback single-origin alias for CORS_ALLOW_ORIGIN
"""
import json
import math
import os
import ssl
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

DEFAULT_PROMPT = "Say hello."
MAX_REQUEST_BYTES = 64 * 1024
MAX_ERROR_DETAIL = 600
MAX_PASSAGES = 50
MAX_TOP_K = 20
MAX_TOP_N = 8


def tls_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if os.environ.get("OPENAI_INSECURE_TLS") == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def json_post(url: str, payload: dict, *, timeout: int = 60) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_DEFAULT_APIKEY']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, context=tls_context(), timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upstream_chat(prompt: str) -> dict:
    base = os.environ["OPENAI_DEFAULT_URL"].rstrip("/")
    model = os.environ["OPENAI_DEFAULT_MODELNAME"]
    return json_post(base + "/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 256,
        "temperature": 0.2,
    })


def embed_texts(texts: str | list[str], input_type: str) -> list[list[float]]:
    payload = {
        "model": os.environ["EMBEDDINGS_MODEL"],
        "input": texts,
        "input_type": input_type,
    }
    data = json_post(normalized_embeddings_url(), payload)
    return [item["embedding"] for item in data["data"]]


def rerank_passages(query: str, passages: list[str]) -> list[dict]:
    model = os.environ["RERANK_MODEL"]
    payload = {
        "model": model,
        "query": {"text": query},
        "passages": [{"text": passage} for passage in passages],
        "truncate": "NONE",
    }
    data = json_post(os.environ["RERANK_URL"], payload)
    return data["rankings"]


def normalized_embeddings_url() -> str:
    url = os.environ["EMBEDDINGS_URL"].rstrip("/")
    if url.endswith("/embeddings"):
        return url
    return url + "/embeddings"


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_mag = math.sqrt(sum(a * a for a in left))
    right_mag = math.sqrt(sum(b * b for b in right))
    if left_mag == 0.0 or right_mag == 0.0:
        return 0.0
    return dot / (left_mag * right_mag)


def cosine_rank(
    query_embedding: list[float],
    passage_embeddings: list[list[float]],
    passages: list[str],
    top_k: int,
) -> list[dict]:
    scored = [
        {
            "index": index,
            "text": passage,
            "score": cosine_similarity(query_embedding, passage_embedding),
        }
        for index, (passage, passage_embedding) in enumerate(zip(passages, passage_embeddings))
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def rag_prompt(query: str, passages: list[str]) -> str:
    formatted = "\n\n".join(f"[{index + 1}] {passage}" for index, passage in enumerate(passages))
    return (
        "Answer the question using only the passages below. "
        "If the passages do not contain the answer, say you do not know from the provided passages.\n\n"
        f"Passages:\n{formatted}\n\nQuestion: {query}"
    )


def parse_positive_int(value, default: int, maximum: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("must be an integer")
    if value < 1:
        raise ValueError("must be at least 1")
    return min(value, maximum)


def upstream_error_response(http_error: urllib.error.HTTPError, stage: str = "upstream") -> dict:
    return {
        "error": stage,
        "detail": http_error.read().decode("utf-8", "replace")[:MAX_ERROR_DETAIL],
    }


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

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BYTES:
            return None, (413, {"error": "request too large"})
        try:
            return json.loads(self.rfile.read(length) or b"{}"), None
        except json.JSONDecodeError:
            return None, (400, {"error": "invalid json"})

    def log_message(self, fmt, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _html(self, code, body):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        path = route_path(self.path)
        if path in {"/", "/healthz", "/info", "/chat", "/rag", "/rag/info"}:
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
        if path == "/rag/info":
            return self._json(200, {
                "chat_backend_url": os.environ.get("OPENAI_DEFAULT_URL"),
                "chat_model": os.environ.get("OPENAI_DEFAULT_MODELNAME"),
                "embeddings_url": os.environ.get("EMBEDDINGS_URL"),
                "embeddings_model": os.environ.get("EMBEDDINGS_MODEL"),
                "rerank_url": os.environ.get("RERANK_URL"),
                "rerank_model": os.environ.get("RERANK_MODEL"),
                "rag_endpoint": "/rag",
                "cors_enabled": bool(os.environ.get("CORS_ALLOW_ORIGIN") or os.environ.get("FRONTEND_ORIGIN")),
            })
        if path == "/":
            return self._html(200, INDEX_HTML)
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        path = route_path(self.path)
        if path == "/rag":
            return self._handle_rag()
        if path != "/chat":
            return self._json(404, {"error": "not found"})
        req, error = self._read_json_body()
        if error:
            return self._json(*error)
        prompt = req.get("prompt") or DEFAULT_PROMPT
        if not isinstance(prompt, str):
            return self._json(400, {"error": "prompt must be a string"})
        try:
            up = upstream_chat(prompt)
        except urllib.error.HTTPError as e:
            return self._json(e.code, upstream_error_response(e))
        except Exception as e:
            return self._json(502, {"error": type(e).__name__, "detail": str(e)[:300]})
        reply = up["choices"][0]["message"]["content"].strip()
        return self._json(200, {"model": up.get("model"), "reply": reply})

    def _handle_rag(self):
        req, error = self._read_json_body()
        if error:
            return self._json(*error)
        query = req.get("query") or req.get("prompt")
        if not isinstance(query, str) or not query.strip():
            return self._json(400, {"error": "query must be a non-empty string"})
        query = query.strip()
        passages = req.get("passages")
        if not isinstance(passages, list) or not passages:
            return self._json(400, {"error": "passages must be a non-empty list of strings"})
        if len(passages) > MAX_PASSAGES:
            return self._json(400, {"error": f"passages must contain at most {MAX_PASSAGES} items"})
        if not all(isinstance(passage, str) and passage.strip() for passage in passages):
            return self._json(400, {"error": "passages must be non-empty strings"})
        passages = [passage.strip() for passage in passages]
        try:
            top_k = parse_positive_int(req.get("top_k"), min(10, len(passages)), min(MAX_TOP_K, len(passages)))
            top_n = parse_positive_int(req.get("top_n"), min(3, top_k), min(MAX_TOP_N, top_k))
        except ValueError as e:
            return self._json(400, {"error": str(e)})

        try:
            query_embedding = embed_texts(query, "query")[0]
            passage_embeddings = embed_texts(passages, "passage")
            candidates = cosine_rank(query_embedding, passage_embeddings, passages, top_k)
            candidate_texts = [candidate["text"] for candidate in candidates]
        except urllib.error.HTTPError as e:
            return self._json(502, upstream_error_response(e, "upstream_embeddings"))
        except KeyError as e:
            return self._json(500, {"error": "missing configuration", "detail": str(e)})
        except Exception as e:
            return self._json(502, {"error": type(e).__name__, "detail": str(e)[:300]})

        try:
            reranked = rerank_passages(query, candidate_texts)
        except urllib.error.HTTPError as e:
            return self._json(502, upstream_error_response(e, "upstream_rerank"))
        except KeyError as e:
            return self._json(500, {"error": "missing configuration", "detail": str(e)})
        except Exception as e:
            return self._json(502, {"error": type(e).__name__, "detail": str(e)[:300]})

        used_passages = []
        used_indexes = []
        for item in reranked[:top_n]:
            candidate_index = item["index"]
            if not isinstance(candidate_index, int) or candidate_index < 0 or candidate_index >= len(candidates):
                continue
            used_passages.append(candidate_texts[candidate_index])
            used_indexes.append(candidates[candidate_index]["index"])
        if not used_passages:
            used_passages = candidate_texts[:top_n]
            used_indexes = [candidate["index"] for candidate in candidates[:top_n]]

        try:
            up = upstream_chat(rag_prompt(query, used_passages))
        except urllib.error.HTTPError as e:
            return self._json(502, upstream_error_response(e, "upstream_chat"))
        except KeyError as e:
            return self._json(500, {"error": "missing configuration", "detail": str(e)})
        except Exception as e:
            return self._json(502, {"error": type(e).__name__, "detail": str(e)[:300]})

        reply = up["choices"][0]["message"]["content"].strip()
        return self._json(200, {
            "model": up.get("model"),
            "embed_model": os.environ.get("EMBEDDINGS_MODEL"),
            "rerank_model": os.environ.get("RERANK_MODEL"),
            "reply": reply,
            "used_passages": used_passages,
            "used_passage_indexes": used_indexes,
        })


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
