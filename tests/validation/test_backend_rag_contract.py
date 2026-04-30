import importlib.util
import json
import os
from pathlib import Path
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib import request as urllib_request
from urllib.error import HTTPError
import unittest

ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = ROOT / "app" / "server.py"


def load_server_module():
    spec = importlib.util.spec_from_file_location("sample_app_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeUpstreamResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def vector_for(text):
    lower = text.lower()
    if "openshift ai" in lower or "rhoai" in lower:
        return [1.0, 0.0, 0.0]
    if "kubernetes" in lower:
        return [0.75, 0.25, 0.0]
    return [0.0, 1.0, 0.0]


@contextmanager
def patched_env(values):
    old = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def running_server(handler):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


class BackendRagContractTest(unittest.TestCase):
    def setUp(self):
        self.server = load_server_module()
        self.urlopen_calls = []
        self.original_urlopen = self.server.urllib.request.urlopen

        def fake_urlopen(req, *args, **kwargs):
            url = getattr(req, "full_url", str(req))
            data = getattr(req, "data", None)
            body = json.loads(data.decode("utf-8")) if data else {}
            self.urlopen_calls.append((url, body, dict(getattr(req, "headers", {}))))

            if "embeddings" in url:
                raw_input = body.get("input", [])
                texts = raw_input if isinstance(raw_input, list) else [raw_input]
                return FakeUpstreamResponse({
                    "model": body.get("model"),
                    "data": [
                        {"index": index, "object": "embedding", "embedding": vector_for(text)}
                        for index, text in enumerate(texts)
                    ],
                })

            if "reranking" in url:
                passages = body.get("passages", [])
                rankings = [
                    {"index": index, "logit": 10.0 - index}
                    for index, _ in enumerate(passages)
                ]
                return FakeUpstreamResponse({"rankings": rankings})

            if url.rstrip("/").endswith("/chat/completions"):
                messages = body.get("messages", [])
                prompt = messages[-1].get("content", "") if messages else ""
                return FakeUpstreamResponse({
                    "model": body.get("model"),
                    "choices": [{"message": {"content": f"RAG answer from prompt: {prompt[:80]}"}}],
                })

            raise AssertionError(f"unexpected upstream URL: {url}")

        self.server.urllib.request.urlopen = fake_urlopen

    def tearDown(self):
        self.server.urllib.request.urlopen = self.original_urlopen

    def post_json(self, base_url, path, payload):
        req = urllib_request.Request(
            base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.original_urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def get_json(self, base_url, path):
        try:
            with self.original_urlopen(base_url + path, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_rag_info_reports_chat_embedding_and_rerank_models(self):
        with patched_env({
            "OPENAI_DEFAULT_URL": "https://chat.example/v1",
            "OPENAI_DEFAULT_APIKEY": "test-key",
            "OPENAI_DEFAULT_MODELNAME": "granite-chat",
            "EMBEDDINGS_URL": "https://embed.example/v1/embeddings",
            "EMBEDDINGS_MODEL": "nvidia/nv-embedqa-e5-v5",
            "RERANK_URL": "https://rerank.example/v1/reranking",
            "RERANK_MODEL": "nvidia/llama-3.2-nv-rerankqa-1b-v2",
        }), running_server(self.server.Handler) as base_url:
            status, payload = self.get_json(base_url, "/rag/info")

        self.assertEqual(status, 200)
        self.assertEqual(payload.get("chat_model"), "granite-chat")
        self.assertEqual(payload.get("embeddings_model"), "nvidia/nv-embedqa-e5-v5")
        self.assertEqual(payload.get("rerank_model"), "nvidia/llama-3.2-nv-rerankqa-1b-v2")
        self.assertEqual(payload.get("rag_endpoint"), "/rag")

    def test_rag_endpoint_embeds_reranks_and_calls_chat_with_used_passages(self):
        passages = [
            "Red Hat OpenShift AI provides tools for model serving and MLOps.",
            "Bananas are yellow fruit and unrelated to the demo.",
            "RHOAI runs model workloads on Kubernetes and OpenShift.",
        ]
        with patched_env({
            "OPENAI_DEFAULT_URL": "https://chat.example/v1",
            "OPENAI_DEFAULT_APIKEY": "test-key",
            "OPENAI_DEFAULT_MODELNAME": "granite-chat",
            "EMBEDDINGS_URL": "https://embed.example/v1/embeddings",
            "EMBEDDINGS_MODEL": "nvidia/nv-embedqa-e5-v5",
            "RERANK_URL": "https://rerank.example/v1/reranking",
            "RERANK_MODEL": "nvidia/llama-3.2-nv-rerankqa-1b-v2",
        }), running_server(self.server.Handler) as base_url:
            status, payload = self.post_json(base_url, "/rag", {
                "query": "What is Red Hat OpenShift AI?",
                "passages": passages,
                "top_k": 2,
                "top_n": 1,
            })

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload.get("model"), "granite-chat")
        self.assertEqual(payload.get("embed_model"), "nvidia/nv-embedqa-e5-v5")
        self.assertEqual(payload.get("rerank_model"), "nvidia/llama-3.2-nv-rerankqa-1b-v2")
        self.assertIn("RAG answer", payload.get("reply", ""))
        self.assertEqual(payload.get("used_passages"), [passages[0]])

        embedding_bodies = [body for url, body, _headers in self.urlopen_calls if "embeddings" in url]
        self.assertIn("query", {body.get("input_type") for body in embedding_bodies})
        self.assertIn("passage", {body.get("input_type") for body in embedding_bodies})
        self.assertTrue(any("reranking" in url for url, _body, _headers in self.urlopen_calls))
        self.assertTrue(any(url.rstrip("/").endswith("/chat/completions") for url, _body, _headers in self.urlopen_calls))

    def test_rag_rejects_invalid_payloads_without_upstream_calls(self):
        with patched_env({
            "OPENAI_DEFAULT_URL": "https://chat.example/v1",
            "OPENAI_DEFAULT_APIKEY": "test-key",
            "OPENAI_DEFAULT_MODELNAME": "granite-chat",
            "EMBEDDINGS_URL": "https://embed.example/v1/embeddings",
            "EMBEDDINGS_MODEL": "nvidia/nv-embedqa-e5-v5",
            "RERANK_URL": "https://rerank.example/v1/reranking",
            "RERANK_MODEL": "nvidia/llama-3.2-nv-rerankqa-1b-v2",
        }), running_server(self.server.Handler) as base_url:
            status, payload = self.post_json(base_url, "/rag", {"query": "ok", "passages": "not-a-list"})

        self.assertEqual(status, 400)
        self.assertIn("error", payload)
        self.assertEqual(self.urlopen_calls, [])


if __name__ == "__main__":
    unittest.main()
