# Austin RHUG 2026 AI sample app GitOps/Tekton harness

This repository demonstrates a Red Hat OpenShift AI chat sample with a Next.js frontend, a Python inference backend, and GitOps/Tekton validation. It is pushed to `https://github.com/dkypuros/austin_rhug_2016.git` and currently has a verified deployment on the lab OpenShift cluster. Normal development and verification should still avoid live-cluster mutation unless an operator explicitly asks for an apply/sync step.

## Current harness state for future agents

Use this section as the fast handoff before making changes. It captures the currently verified direction of the sample app and the cluster automation surfaces.

### Verified live deployment

- **GitHub repo:** `https://github.com/dkypuros/austin_rhug_2016.git`
- **Branch:** `main`
- **Current app direction:** the sample app now targets the OpenShift AI/RHOAI `vllm` model deployment shown in the OpenShift AI dashboard, not the NVIDIA-hosted NGC endpoint.
- **OpenShift app namespace:** `composer-ai-apps-demo`
- **OpenShift AI model namespace:** `composer-ai-apps`
- **Frontend route for review:** `https://sample-chat-composer-ai-apps-demo.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com`
- **Backend route for direct API smoke tests:** `https://sample-chat-api-composer-ai-apps-demo.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com`
- **RHOAI vLLM inference route:** `https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/v1`
- **Model id:** `vllm`

The source of truth for the deployed inference target is:

```yaml
# manifests/sample-app/10-configmap-code.yaml
OPENAI_DEFAULT_URL: https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/v1
OPENAI_DEFAULT_MODELNAME: vllm
```

The live RHOAI route accepts OpenAI-compatible chat calls without a real bearer token. The backend still expects `OPENAI_DEFAULT_APIKEY` to exist because it shares the same provider contract with authenticated endpoints; for this vLLM route, keep the cluster `llm-credentials` Secret as a harmless placeholder unless switching back to a provider that requires a real key.

### Argo CD / OpenShift GitOps state

Argo CD resources live in `gitops/argocd/`:

- `gitops/argocd/sample-app-project.yaml`
- `gitops/argocd/sample-app-application.yaml`

Expected live state:

```sh
oc -n openshift-gitops get app sample-app
# SYNC STATUS: Synced
# HEALTH STATUS: Healthy
```

The Argo CD Application tracks:

```text
repoURL: https://github.com/dkypuros/austin_rhug_2016.git
targetRevision: main
path: manifests/sample-app
destination namespace: composer-ai-apps-demo
```

If you change manifests under `manifests/sample-app/`, push first, then refresh/sync Argo CD to the pushed Git revision. Do not assume the cluster is using unpushed local files.

### Tekton / OpenShift Pipelines state

Tekton resources live in `tekton/`:

- `tekton/tasks/validate-sample-app.yaml` renders `manifests/sample-app` with `oc kustomize`, rejects inline Secrets, and dry-runs the rendered OpenShift resources with `oc apply --dry-run=client`.
- `tekton/tasks/build-sample-app-image.yaml` builds/pushes one image with Buildah.
- `tekton/pipelines/sample-app-ci.yaml` validates manifests, then builds backend and frontend images in parallel.

Expected live checks:

```sh
oc -n composer-ai-apps-demo get pipeline sample-app-ci
oc -n composer-ai-apps-demo get task validate-sample-app build-sample-app-image
```

The Buildah task currently needs the `pipeline` service account to be allowed to use the privileged SCC on this lab cluster. That was granted during verification because the default `pipelines-scc` rejected privileged Buildah pods. Treat this as a lab/demo setting, not a production default.

The reusable pipeline expects a workspace named `source` containing a checkout of this repository. Do not commit cluster-specific PipelineRuns, PVCs, credentials, or workspace seed pods unless the user explicitly asks for a reusable environment overlay.

### Safe smoke-test commands

After a deploy or Argo sync, verify the harness with:

```sh
FRONTEND_HOST=$(oc -n composer-ai-apps-demo get route sample-chat -o jsonpath='{.spec.host}')

curl -k -sS "https://$FRONTEND_HOST/api/info"

curl -k -sS "https://$FRONTEND_HOST/api/chat" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Reply with exactly: vLLM smoke test"}'
```

Expected `/api/info` essentials:

```json
{
  "backend_url": "https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/v1",
  "model": "vllm"
}
```

### Harness guardrails

- Prefer reading this README, `CLAUDE.md`, and `manifests/sample-app/README.md` before changing deployment behavior.
- Keep real `.env_*`, kubeconfig, tokens, `.omx/`, `.omc/`, generated build output, `frontend/node_modules/`, and `frontend/.next/` out of Git.
- If a user asks for a checkpoint before a pivot, create a small commit first, push it, then isolate the pivot in a follow-up commit.
- For endpoint changes, update `manifests/sample-app/10-configmap-code.yaml`, verify `/api/info`, verify `/api/chat`, then commit/push.
- When reporting completion, include the Git commit, Argo CD status, Tekton status if relevant, and the public route.

## What is included

```text
README.md                          # Project harness instructions
CLAUDE.md                          # AI-agent safety and validation instructions
app/                               # Python OpenAI-compatible inference backend
  server.py                        # Exposes /healthz, /info, and POST /chat
  chat.py                          # CLI chat helper using the same env contract
  .env.nvidia.example              # Safe NVIDIA example values only
  .env.rhoai.example               # Safe RHOAI example values only
frontend/                          # Next.js App Router UI with shadcn-style components
manifests/sample-app/              # OpenShift sample app manifests for frontend + backend
  README.md
  00-namespace.yaml
  20-secret.yaml.example           # Template only; never commit real Secret values
gitops/argocd/                     # Argo CD AppProject/Application definitions
tekton/                            # Tekton validation/build tasks and pipelines
docs/access.md                     # Access runbook for GitHub/NVIDIA/OpenShift
docs/gh-cli-usage.md               # GitHub CLI quick reference
.env_gh_cli.example                # Safe GitHub CLI env template
.env_NVIDIA.example                # Safe NVIDIA env template
.env_openshift_lab.example         # Safe OpenShift/RHDP env template
.gitignore                         # Secret/runtime ignore policy
```

Keep the architecture stable: browser traffic goes to the Next.js frontend, the frontend calls the Python backend, and the backend is the only component that talks to the OpenAI-compatible inference endpoint.

## Runtime architecture

```text
Browser
  -> Next.js frontend (shadcn-style chat UI)
      -> Python backend /info and /chat
          -> OpenAI-compatible endpoint (NVIDIA NGC or RHOAI vLLM)
```

- **Frontend:** Next.js App Router UI under `frontend/`. It displays backend/model info, accepts prompts, submits chat requests through a configured backend URL or frontend API/proxy, and surfaces latency/error details.
- **Backend:** `app/server.py` preserves the demo contract:
  - `GET /healthz` for readiness/liveness
  - `GET /info` for backend/model metadata
  - `POST /chat` with a prompt payload and OpenAI-compatible response semantics
- **Inference configuration:** The backend continues to use:
  - `OPENAI_DEFAULT_URL`
  - `OPENAI_DEFAULT_APIKEY`
  - `OPENAI_DEFAULT_MODELNAME`
  - optional `OPENAI_INSECURE_TLS` for lab-only self-signed TLS cases
- **GitOps:** Argo CD should sync declarative app resources from `manifests/sample-app/`; manual sync is preferred for demo safety.
- **Tekton:** Pipelines should validate YAML/Kustomize/static secret policy and, when feasible, build or lint the frontend/backend images.

## Security defaults

- Do not commit real `.env_*`, `.env`, `.omx/`, `.omc/`, kubeconfig, key, certificate, token, generated runtime log, or local agent-state files.
- `.gitignore` is intentionally broad because this repo contains deployment examples and local AI-agent runtime state.
- Do not print secret values in terminal output, docs, commits, issues, pull requests, PipelineRuns, or task logs.
- Use temporary `KUBECONFIG` files for OpenShift validation.
- Use pre-created cluster secrets referenced by name, Sealed Secrets, or External Secrets for future secret delivery. Never commit inline secret values.
- Commit only `.example` files for secrets. `manifests/sample-app/20-secret.yaml.example` is a template, not a deployable secret for GitOps.
- Do not mutate a live cluster from automated verification unless the operator explicitly asks for an apply/sync step.

## Local prerequisites

Recommended tools:

- Node.js and npm for the Next.js frontend checks, if `frontend/package.json` is present
- Python 3 for backend local execution and static helper checks
- `gh` for GitHub CLI workflows
- `kubectl` or `oc` for Kustomize rendering and client-side manifest validation
- OpenShift GitOps/Argo CD installed in the target cluster for `Application` sync
- OpenShift Pipelines/Tekton installed in the target cluster for pipeline execution

See `docs/access.md` for environment-file and cluster access patterns. Keep real environment files local and ignored.

## Run locally

### Backend

Use one of the safe example env files, then run the Python backend or CLI helper:

```sh
cp app/.env.rhoai.example app/.env.rhoai
# edit app/.env.rhoai locally if the lab route changes; never commit it
set -a; source app/.env.rhoai; set +a
python3 app/server.py
```

The backend listens on `PORT` when set and defaults to its built-in port otherwise. Validate the contract with:

```sh
curl -s http://localhost:8080/healthz
curl -s http://localhost:8080/info
curl -s -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"In one sentence, what is Red Hat OpenShift AI?"}'
```

### Frontend

When the `frontend/` lane is present:

```sh
cd frontend
npm install
npm run lint
npm run build
```

Configure the frontend to reach the backend using the env names documented by `frontend/` (for example a server-side backend URL such as `BACKEND_URL`). Do not place the inference API key in frontend/browser-exposed variables; only the backend should receive `OPENAI_DEFAULT_APIKEY`.

## Validate locally

Run static checks before reporting completion or opening a pull request:

```sh
python3 - <<'PY'
from pathlib import Path
try:
    import yaml
except Exception as exc:
    raise SystemExit(f'PyYAML unavailable: {exc}')
paths = [p for root in ('apps', 'gitops', 'manifests', 'tekton') if Path(root).exists() for p in Path(root).rglob('*.yaml')]
for path in paths:
    with path.open() as f:
        list(yaml.safe_load_all(f))
    print(f'parsed {path}')
PY
```

Render Kustomize paths when available:

```sh
kubectl kustomize apps/hello-world
kubectl kustomize manifests/sample-app
```

Run a client-side dry-run if `oc` is available and a temporary authenticated kubeconfig is set:

```sh
oc kustomize manifests/sample-app | oc apply --dry-run=client --validate=false -f -
```

`kubectl kustomize` or `oc kustomize` can render without cluster credentials. The dry-run apply step may still attempt API discovery, and the sample includes OpenShift `Route` resources, so prefer `oc apply --dry-run=client` with the current lab kubeconfig when validating the full rendered bundle.

## Deploy with Argo CD / OpenShift GitOps

After the repository is pushed to GitHub and OpenShift GitOps is installed, apply the Argo CD AppProject and Application manifests from an authenticated admin/operator shell:

```sh
oc apply -f gitops/argocd/sample-app-project.yaml
oc apply -f gitops/argocd/sample-app-application.yaml
```

Expected sample-app GitOps shape:

- repo: `https://github.com/dkypuros/austin_rhug_2016.git`
- revision: `main` for the current lab harness, or a reviewed release branch/tag if promoted later
- path: `manifests/sample-app`
- destination namespace: `composer-ai-apps-demo`

Sync should remain manual by default to avoid surprising cluster mutations in the initial harness.

## Validate with Tekton

The Tekton Pipeline expects a workspace named `source` containing a checkout of this repository. Reusable `Task` and `Pipeline` definitions belong under `tekton/`; avoid committing cluster-specific `PipelineRun` credentials or workspaces.

Apply Tekton definitions only when OpenShift Pipelines is installed and live-cluster mutation is intended:

```sh
oc -n composer-ai-apps-demo apply -f tekton/tasks/validate-sample-app.yaml
oc -n composer-ai-apps-demo apply -f tekton/tasks/build-sample-app-image.yaml
oc -n composer-ai-apps-demo apply -f tekton/pipelines/sample-app-ci.yaml
```

Then create an environment-specific `PipelineRun` that binds a `source` workspace containing this repository checkout. On the current lab cluster, the Buildah image-build task requires the `pipeline` service account to be permitted to use the privileged SCC; keep that as a lab-specific operational grant rather than a production recommendation.

## GitHub workflow

The target repository has been created as a private repo:

```text
https://github.com/dkypuros/austin_rhug_2016
```

Before pushing:

1. Re-run secret scan and manifest validation.
2. Run frontend install/lint/build if `frontend/package.json` exists.
3. Confirm `git status` does not include real `.env_*`, `.env`, `.omx/`, `.omc/`, kubeconfig, key/cert, or generated log files.
4. Commit with a Lore-style commit message.
5. Push only after explicit user instruction.
