# Sample chat app — GitOps/OpenShift

This directory contains the OpenShift sample-app manifests for the Austin RHUG AI chat demo. The target shape is a two-tier app in a dedicated namespace:

```text
Route/Service: sample-chat-frontend
  -> Next.js frontend
      -> Service: sample-chat-backend
          -> Python backend /info, /chat, /rag/info, and /rag
              -> OpenShift AI vLLM chat endpoint
              -> hosted NVIDIA embeddings/reranker endpoints for Phase A RAG
```

The namespace is `composer-ai-apps-demo` so the demo does not touch live `composer-ai-apps` workloads.

## Runtime contract

The backend Deployment owns the inference credentials and provider configuration. Keep these env vars compatible with `app/server.py` and the CLI helper:

```text
OPENAI_DEFAULT_URL        e.g. https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/v1
OPENAI_DEFAULT_APIKEY     from Secret llm-credentials, key apiKey
OPENAI_DEFAULT_MODELNAME  e.g. vllm                          (RHOAI vLLM)
                          or  meta/llama-3.1-8b-instruct     (NVIDIA NGC)
OPENAI_INSECURE_TLS       optional lab-only escape hatch for self-signed TLS
EMBEDDINGS_URL            hosted NVIDIA embeddings endpoint for Phase A RAG
EMBEDDINGS_MODEL          e.g. nvidia/nv-embedqa-e5-v5
RERANK_URL                hosted NVIDIA reranker endpoint for Phase A RAG; URL slug uses llama-3_2
RERANK_MODEL              e.g. nvidia/llama-3.2-nv-rerankqa-1b-v2
```

Phase A RAG uses hosted NVIDIA retrieval for embeddings/reranking while preserving the existing RHOAI vLLM chat endpoint. It does not add file upload, document ingestion, or persistent vector storage; the frontend passes ad-hoc passages to the backend for retrieval.

`OPENAI_DEFAULT_APIKEY` can remain a harmless placeholder for the current RHOAI vLLM chat route, but a real NVIDIA API key in the `llm-credentials` Secret is required before hosted NVIDIA embeddings or reranking will work.

Frontend configuration should contain only a backend service URL or proxy target. Never put `OPENAI_DEFAULT_APIKEY` or provider API keys in browser-visible frontend variables.

The kustomization points both deployments at the OpenShift internal registry:

| File | Purpose |
|---|---|
| `00-namespace.yaml` | dedicated namespace, isolated from `composer-ai-apps` |
| `20-secret.yaml.example` | template for `llm-credentials` Secret; do not apply or commit real values |
| backend Deployment/Service files | run `app/server.py`, expose `/healthz`, `/info`, and `/chat` inside the namespace |
| frontend Deployment/Service/Route files | run the Next.js UI and expose the browser entrypoint |
| `kustomization.yaml` | expected render entrypoint for Argo CD and local validation, when present |

Some file names may change as the manifest lane migrates from the original single-container sample. Preserve the frontend/backend separation and the secret boundary above.

## Current live verification

As of the issue #2 closeout, this manifest path has been synced by Argo CD and verified live with:

- `GET /rag/info` returning `chat_model=vllm`, `embeddings_model=nvidia/nv-embedqa-e5-v5`, and `rerank_model=nvidia/llama-3.2-nv-rerankqa-1b-v2`;
- `POST /rag` returning HTTP 200 with `reply`, `used_passages`, and `used_passage_indexes`;
- frontend route rendering the Chat/RAG UI.

`llm-credentials` is still created out of band. It must contain the real NVIDIA API key for hosted retrieval to work, but the value must never be committed.

## Local validation

From the repository root, run static validation before applying anything to a cluster:

```sh
python3 - <<'PY'
from pathlib import Path
try:
    import yaml
except Exception as exc:
    raise SystemExit(f'PyYAML unavailable: {exc}')
for path in Path('manifests/sample-app').rglob('*.yaml'):
    with path.open() as f:
        list(yaml.safe_load_all(f))
    print(f'parsed {path}')
PY
```

If `kustomization.yaml` exists:

```sh
kubectl kustomize manifests/sample-app
kubectl kustomize manifests/sample-app | kubectl apply --dry-run=client --validate=false -f -
```

`kubectl apply --dry-run=client` can still attempt API discovery depending on the local client. If that happens, use an authenticated temporary kubeconfig or record YAML/Kustomize validation instead.

## GitOps with Argo CD

The sample-app Argo CD `Application` should point at this directory:

```text
repoURL: https://github.com/dkypuros/austin_rhug_2016.git
targetRevision: reviewed release branch or tag
path: manifests/sample-app
destination namespace: composer-ai-apps-demo
```

Keep sync manual by default for demo safety. Applying the Argo CD `AppProject`/`Application` is a live-cluster mutation and should only be done when explicitly requested by an operator.

## Tekton validation/build flow

Tekton resources should validate this path from a `source` workspace and fail fast on unsafe secrets. Desired coverage:

1. Parse YAML under `manifests/sample-app/`, `gitops/`, and `tekton/`.
2. Render `manifests/sample-app` with Kustomize when `kustomization.yaml` exists.
3. Refuse rendered inline `Secret` resources containing real values.
4. Run frontend install/lint/build when `frontend/package.json` exists.
5. Run backend smoke/static checks for `app/server.py` without printing credentials.

Cluster-specific `PipelineRun` workspace bindings and credentials should stay uncommitted.

## Manual apply outline

Only run these commands from an authenticated operator shell when live-cluster mutation is intended:

```sh
cd /path/to/austin_rhug_2026
set -a; source .env_openshift_lab; set +a
export KUBECONFIG="$(mktemp -d)/kubeconfig"
oc login "$OPENSHIFT_API_URL" -u "$OPENSHIFT_ADMIN_USER" -p "$OPENSHIFT_ADMIN_PASSWORD"

oc apply -f manifests/sample-app/00-namespace.yaml

# Create the backend Secret from local, ignored credentials. Do not commit the rendered Secret.
# The existing RHOAI vLLM chat endpoint accepts a placeholder key, but hosted
# NVIDIA retrieval requires a real NVIDIA API key.
set -a; source .env_NVIDIA; set +a
oc -n composer-ai-apps-demo create secret generic llm-credentials \
  --from-literal=apiKey="$NVIDIA_API_KEY" \
  --dry-run=client -o yaml | oc apply -f -

# Prefer Kustomize/Argo CD once kustomization.yaml is present.
kubectl kustomize manifests/sample-app | oc apply -f -
```

## Promote to the on-cluster vLLM endpoint

Promote by changing backend configuration only; the frontend and `/chat` contract should not change. In GitOps, commit the config update through the manifest path and let Argo CD sync it. For an imperative lab-only demonstration:

```sh
oc -n composer-ai-apps-demo set env deploy/sample-chat-backend \
  OPENAI_DEFAULT_URL=https://vllm-composer-ai-apps.apps.cluster.example/v1 \
  OPENAI_DEFAULT_MODELNAME=vllm \
  OPENAI_INSECURE_TLS=1
```

Use the real route for the lab cluster, but do not commit cluster-specific hostnames or real credentials unless they are intentional public examples.
