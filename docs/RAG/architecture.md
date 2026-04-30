# RAG architecture for the demo app

Reference for the RAG path tracked in [issue #2](https://github.com/dkypuros/austin_rhug_2016/issues/2). The chat path (issue #1) already swaps backends by config; this doc captures how to add embeddings + reranking on the same seam.

## Flow

```
user query ─► /rag (backend)
              ├─ embed(query)                ── EMBEDDINGS_URL / EMBEDDINGS_MODEL
              ├─ embed(passages)             ── same
              ├─ cosine top_k in-process
              ├─ rerank(top_k)               ── RERANK_URL / RERANK_MODEL
              └─ chat-completion with top_n  ── OPENAI_DEFAULT_URL / OPENAI_DEFAULT_MODELNAME
```

Three independent backends behind one HTTP route. Each can be promoted to an in-cluster equivalent without backend code changes.

## Configuration contract

Backend reads, in addition to the chat-path vars (`OPENAI_DEFAULT_URL`, `OPENAI_DEFAULT_APIKEY`, `OPENAI_DEFAULT_MODELNAME`):

| Var | Example (NVIDIA NGC) | Example (in-cluster) |
|---|---|---|
| `EMBEDDINGS_URL` | `https://integrate.api.nvidia.com/v1/embeddings` | `https://embeddings-composer-ai-apps.apps.<cluster>/v1/embeddings` |
| `EMBEDDINGS_MODEL` | `nvidia/nv-embedqa-e5-v5` | id from in-cluster `/v1/models` |
| `RERANK_URL` | `https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-3.2-nv-rerankqa-1b-v2/reranking` | in-cluster reranker route |
| `RERANK_MODEL` | `nvidia/llama-3.2-nv-rerankqa-1b-v2` | matching id |

`OPENAI_DEFAULT_APIKEY` covers all three NVIDIA surfaces with one bearer token. In-cluster routes can use any placeholder.

## HTTP shapes

### `POST /rag`

```json
{ "query": "...", "passages": ["...", "..."], "top_k": 10, "top_n": 3 }
```

Response:

```json
{
  "model": "meta/llama-3.1-8b-instruct",
  "embed_model": "nvidia/nv-embedqa-e5-v5",
  "rerank_model": "nvidia/llama-3.2-nv-rerankqa-1b-v2",
  "reply": "...",
  "used_passages": ["..."]
}
```

### `GET /rag/info`

Mirrors `/info` but reports all three configured backends so the UI can render embed/rerank/chat pills.

## Upstream NVIDIA APIs

Already documented at [`docs/NVIDIA Models/embeddings-and-rerankers.md`](../NVIDIA%20Models/embeddings-and-rerankers.md):

- Embeddings: `POST /v1/embeddings` on `integrate.api.nvidia.com`, requires `input_type: "query" | "passage"`.
- Rerank: `POST /v1/retrieval/<model>/reranking` on `ai.api.nvidia.com` — different host, per-model URL, returns `rankings[]` ordered by `logit`.

## Promotion plan

| Stage | Phase 1 (NGC) | Promoted (in-cluster KServe) |
|---|---|---|
| Embed | NVIDIA NIM | `InferenceService` running an embeddings modelcar (e.g. nv-embedqa-e5-v5 OCI image) |
| Rerank | NVIDIA NIM | `InferenceService` running a reranker NIM |
| Chat | NVIDIA NIM | existing `composer-ai-apps/vllm` Granite endpoint |

The promotion is the same shape as Act 3 in [issue #1](https://github.com/dkypuros/austin_rhug_2016/issues/1): change four ConfigMap values, commit, let Argo CD sync.

## Build instructions

Step-by-step build is in [issue #2](https://github.com/dkypuros/austin_rhug_2016/issues/2) under "Build instructions" — preflight, backend helpers, local smoke test, frontend toggle, manifest changes, cluster apply, on-cluster promotion.

## Related references

- [`docs/NVIDIA Models/embeddings-and-rerankers.md`](../NVIDIA%20Models/embeddings-and-rerankers.md) — endpoint shapes, request bodies, entitlement gotcha.
- [`docs/RHOAI Reference/`](../RHOAI%20Reference/) — runtime / model-deployment / inference-endpoint reference for promoting any of these on-cluster.
- [`docs/manual_commands/inspect-inferenceservice.md`](../manual_commands/inspect-inferenceservice.md) — `oc` one-liner for verifying any new InferenceService.
