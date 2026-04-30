# Accomplished so far

This is the high-level handoff for the Austin RHUG sample app as of the issue #2 completion.

## 1. Repository and harness

- Created the GitHub repository: `https://github.com/dkypuros/austin_rhug_2016`.
- Added AI-harness guidance in `README.md`, `CLAUDE.md`, and supporting docs.
- Established secret hygiene with ignored real `.env_*` files and committed `.example` templates only.

## 2. Application

- Added a Python backend in `app/server.py`.
- Added a Next.js App Router frontend with shadcn-style local components.
- Deployed frontend and backend as separate OpenShift workloads in `composer-ai-apps-demo`.
- Exposed two routes:
  - frontend: `https://sample-chat-composer-ai-apps-demo.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/`
  - backend: `https://sample-chat-api-composer-ai-apps-demo.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/`

## 3. OpenShift AI vLLM pivot

- Identified the OpenShift AI vLLM endpoint in the `composer-ai-apps` namespace.
- Updated the sample backend config to use:
  - `OPENAI_DEFAULT_URL=https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/v1`
  - `OPENAI_DEFAULT_MODELNAME=vllm`
- Verified `/chat` responds through the OpenShift AI vLLM route.

## 4. GitOps and Tekton

- Added Argo CD AppProject/Application resources under `gitops/argocd/`.
- Argo CD `sample-app` tracks `main` and `manifests/sample-app`.
- Added Tekton tasks/pipeline under `tekton/` for manifest validation and image builds.
- Added Tekton validation for RAG retrieval env wiring.

## 5. Issue #2: Phase A RAG

Implemented the RAG lane beside the existing chat lane:

```text
Browser
  -> Next.js frontend RAG mode
      -> Python backend /rag
          -> NVIDIA embeddings
          -> NVIDIA reranker
          -> OpenShift AI vLLM chat generation
```

The implementation includes:

- `GET /rag/info` for chat/embed/rerank metadata.
- `POST /rag` for supplied-passage retrieval and grounded answer generation.
- Frontend Chat/RAG toggle.
- Passage textarea, no file upload or persistent vector store.
- Model pills for chat/embed/rerank.
- Used-passages display.
- Manifest env vars for `EMBEDDINGS_*` and `RERANK_*`.
- Backend, frontend, and manifest contract tests.

## 6. Live verification evidence

The RAG route was verified live after refreshing the backend Secret with a real NVIDIA key. A successful response shape was:

```json
{
  "model": "vllm",
  "embed_model": "nvidia/nv-embedqa-e5-v5",
  "rerank_model": "nvidia/llama-3.2-nv-rerankqa-1b-v2",
  "reply": "Based on the provided passages, OpenShift AI runs models on GPU nodes.",
  "used_passages": [
    "OpenShift AI ships vLLM model serving for GPUs.",
    "KServe exposes model inference endpoints on OpenShift."
  ],
  "used_passage_indexes": [0, 2]
}
```

## 7. How to demo it

1. Open the frontend route.
2. In **Chat** mode, ask a normal question to show direct vLLM chat.
3. Switch to **RAG** mode.
4. Keep or paste passages, ask a question about them, and click **Run RAG**.
5. Point out the selected **Used passages** and the three model pills.

## 8. Remaining future work

- Promote embeddings/reranking to in-cluster equivalents by changing `EMBEDDINGS_*` and `RERANK_*` config values once those services exist.
- Optionally add a reusable, committed PipelineRun overlay if the demo needs one; keep credentials/workspaces environment-specific.
- Optionally tag a release once the talk/demo baseline is frozen.
