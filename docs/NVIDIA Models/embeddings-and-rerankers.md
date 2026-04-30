# NVIDIA NIM — Embeddings and Rerankers

Reference for calling NVIDIA's hosted embedding and reranker NIMs from this repo. Useful for the RAG side of any demo (embed query + corpus → rerank top-K).

The two services live on **two different base URLs**:

| Service | Base URL | Endpoint | Listed in `/v1/models`? |
|---|---|---|---|
| Chat completions | `https://integrate.api.nvidia.com/v1` | `/chat/completions` | yes |
| Embeddings | `https://integrate.api.nvidia.com/v1` | `/embeddings` | yes |
| Reranking | `https://ai.api.nvidia.com/v1/retrieval/<model>` | `/reranking` | **no** — per-model URL |

Auth is the same on both: `Authorization: Bearer $NVIDIA_API_KEY`.

## Load env

```sh
cd /Users/davidkypuros/Documents/Git_ONLINE/austin_rhug_2026
set -a; source .env_NVIDIA; set +a
# NVIDIA_API_KEY=...
# NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

---

## 1. Embeddings — `/v1/embeddings`

OpenAI-compatible shape, with one NIM-specific field: `input_type` is required and must be `"query"` or `"passage"` (use `query` for the user's question, `passage` for documents you index).

### Models confirmed listed for the demo key

```text
nvidia/nv-embedqa-e5-v5
nvidia/nv-embedqa-mistral-7b-v2
nvidia/nv-embed-v1
nvidia/nv-embedcode-7b-v1
nvidia/llama-3.2-nv-embedqa-1b-v1
nvidia/llama-3.2-nv-embedqa-1b-v2
nvidia/llama-3.2-nemoretriever-300m-embed-v1
nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1
nvidia/llama-nemotron-embed-1b-v2
nvidia/llama-nemotron-embed-vl-1b-v2
nvidia/embed-qa-4
snowflake/arctic-embed-l
```

(Confirm at any time with `curl -sS "$NVIDIA_BASE_URL/models" -H "Authorization: Bearer $NVIDIA_API_KEY" | jq -r '.data[].id' | grep -iE 'embed|retriever'`.)

### curl

```sh
curl -sS "$NVIDIA_BASE_URL/embeddings" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/nv-embedqa-e5-v5",
    "input": "What is Red Hat OpenShift AI?",
    "input_type": "query"
  }'
```

Response (truncated):

```json
{
  "object": "list",
  "data": [
    { "index": 0, "embedding": [-0.027, -0.007, ...], "object": "embedding" }
  ],
  "model": "nvidia/nv-embedqa-e5-v5",
  "usage": { "prompt_tokens": 8, "total_tokens": 8 }
}
```

### Python (stdlib only — same shape used in `app/chat.py`)

```python
import json, os, urllib.request
def embed(texts, *, input_type="passage", model="nvidia/nv-embedqa-e5-v5"):
    body = json.dumps({"model": model, "input": texts, "input_type": input_type}).encode()
    req = urllib.request.Request(
        os.environ["NVIDIA_BASE_URL"].rstrip("/") + "/embeddings",
        data=body, method="POST",
        headers={
            "Authorization": "Bearer " + os.environ["NVIDIA_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return [d["embedding"] for d in json.loads(r.read())["data"]]
```

`input` accepts a string or a list of strings — batch your passages.

---

## 2. Rerankers — `/v1/retrieval/<model>/reranking`

Reranker NIMs are *not* listed by `/v1/models`. Each model has its own URL on a different host (`ai.api.nvidia.com`, not `integrate.api.nvidia.com`). Discover them on `build.nvidia.com` under "Retrieval QA".

Common reranker model IDs:

```text
nvidia/llama-3.2-nv-rerankqa-1b-v2
nvidia/nv-rerankqa-mistral-4b-v3
```

### curl

```sh
MODEL="nvidia/llama-3.2-nv-rerankqa-1b-v2"
MODEL_PATH="nvidia/llama-3_2-nv-rerankqa-1b-v2"
curl -sS "https://ai.api.nvidia.com/v1/retrieval/${MODEL_PATH}/reranking" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$MODEL"'",
    "query":   { "text": "What is Red Hat OpenShift AI?" },
    "passages": [
      { "text": "Red Hat OpenShift AI is an enterprise AI platform." },
      { "text": "Bananas are yellow fruit." }
    ],
    "truncate": "NONE"
  }'
```

The response is a list of `{ "index": N, "logit": ... }` ordered by relevance — apply that order back to your original passages.

The hosted llama-3.2 reranker URL slug currently uses `llama-3_2` while the JSON `model` value remains `nvidia/llama-3.2-nv-rerankqa-1b-v2`.

### Python helper

```python
import json, os, urllib.request
def rerank(query, passages, *, model="nvidia/llama-3.2-nv-rerankqa-1b-v2"):
    # The hosted URL slug uses 3_2 while the JSON model id remains 3.2.
    model_path = model.replace("llama-3.2-", "llama-3_2-")
    url = f"https://ai.api.nvidia.com/v1/retrieval/{model_path}/reranking"
    body = json.dumps({
        "model": model,
        "query": {"text": query},
        "passages": [{"text": p} for p in passages],
        "truncate": "NONE",
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": "Bearer " + os.environ["NVIDIA_API_KEY"],
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        ranked = json.loads(r.read())["rankings"]
    return [(passages[item["index"]], item.get("logit")) for item in ranked]
```

---

## Entitlement gotcha

Same caveat as the chat models: a model id can be visible on `build.nvidia.com` and still return:

```json
{"status":404,"title":"Not Found","detail":"Function '...': Not found for account '...'"}
```

That means your key isn't entitled to invoke the function (separate from listing/visibility). The fix is to open the model card on `build.nvidia.com` while signed in to the account that owns `NVIDIA_API_KEY` and click "Try API" / "Get API Key" — that provisions the function on your account.

`nv-embedqa-e5-v5` is confirmed working on the demo key. `nv-rerankqa-mistral-4b-v3` returned the entitlement 404 in this lab; if you need rerankers, provision them through the build.nvidia.com flow first.

## Why this matters for the demo

A full RAG path is `embed query + corpus → vector search → rerank top-K → chat-completion`. Today's demo only exercises chat-completion. If the talk wants to show RAG against the same on-cluster Granite, you can prototype the embed + rerank steps against NVIDIA NIMs (NGC) and later promote them onto in-cluster equivalents (e.g. KServe-served `nvidia/nv-embedqa-e5-v5` modelcar, plus a TEI/vLLM reranker) using the same env-var seam the chat path already uses.
