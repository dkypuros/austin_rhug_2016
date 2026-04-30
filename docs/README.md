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
| `RERANK_URL` | `https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-3.2-nv-rerankqa-1b-v2/reranking` |
| `RERANK_MODEL` | `nvidia/llama-3.2-nv-rerankqa-1b-v2` |

`OPENAI_DEFAULT_APIKEY` is still read from the backend `llm-credentials` Secret. For the existing RHOAI vLLM chat endpoint, the secret can remain a harmless placeholder. A real NVIDIA API key is required only when exercising the hosted NVIDIA embeddings or reranker endpoints.

See also:

- [`RAG/architecture.md`](RAG/architecture.md) for the RAG endpoint contract and promotion path.
- [`NVIDIA Models/embeddings-and-rerankers.md`](NVIDIA%20Models/embeddings-and-rerankers.md) for NVIDIA request shapes and entitlement notes.
