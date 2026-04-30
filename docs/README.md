# Austin RHUG demo docs

This directory contains runbooks and reference notes for the Austin RHUG 2026 sample app.

## Phase A RAG direction

Phase A keeps chat generation on the existing OpenShift AI/RHOAI vLLM backend and adds a hosted NVIDIA retrieval path for RAG:

```text
Browser
  -> Next.js frontend
      -> Python backend
          -> RHOAI vLLM chat endpoint
          -> hosted NVIDIA embeddings and reranker endpoints
```

The Phase A RAG flow accepts user-supplied passages in the UI. It does not add file upload, document ingestion, or persistent vector storage.

The manifest seam for retrieval is:

| Variable | Hosted NVIDIA Phase A value |
|---|---|
| `EMBEDDINGS_URL` | `https://integrate.api.nvidia.com/v1/embeddings` |
| `EMBEDDINGS_MODEL` | `nvidia/nv-embedqa-e5-v5` |
| `RERANK_URL` | `https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-3_2-nv-rerankqa-1b-v2/reranking` |
| `RERANK_MODEL` | `nvidia/llama-3.2-nv-rerankqa-1b-v2` |

`OPENAI_DEFAULT_APIKEY` is still read from the backend `llm-credentials` Secret. For the existing RHOAI vLLM chat endpoint, the secret can remain a harmless placeholder. A real NVIDIA API key is required only when exercising the hosted NVIDIA embeddings or reranker endpoints.

See also:

- [`RAG/architecture.md`](RAG/architecture.md) for the RAG endpoint contract and promotion path.
- [`NVIDIA Models/embeddings-and-rerankers.md`](NVIDIA%20Models/embeddings-and-rerankers.md) for NVIDIA request shapes and entitlement notes.


## Current completed demo state

The repository now demonstrates both paths live on OpenShift:

1. **Chat path:** Next.js frontend -> Python backend `/chat` -> OpenShift AI `vllm` route.
2. **RAG path:** Next.js frontend -> Python backend `/rag` -> hosted NVIDIA embeddings -> hosted NVIDIA reranker -> OpenShift AI `vllm` route.

The public review route is:

```text
https://sample-chat-composer-ai-apps-demo.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/
```

Use Chat mode for a direct vLLM smoke test. Use RAG mode with supplied passages to show retrieval, reranking, selected passages, and grounded vLLM generation.

Important implementation detail: the hosted NVIDIA reranker URL uses the route slug `llama-3_2-nv-rerankqa-1b-v2`, while the JSON request body model id remains `nvidia/llama-3.2-nv-rerankqa-1b-v2`. Keep those distinct.

For the full operator walkthrough, use the root [`README.md`](../README.md).
