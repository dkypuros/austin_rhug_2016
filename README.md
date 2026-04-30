# Austin RHUG 2026 AI sample app GitOps/Tekton harness

This repository demonstrates a Red Hat OpenShift AI chat sample with a Next.js frontend, a Python inference backend, and local-first GitOps/Tekton validation. It is intended to be pushed later to `https://github.com/dkypuros/austin_rhug_2016.git`, but normal development and verification should not mutate a live cluster unless an operator explicitly chooses to apply manifests.

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

Some lanes may add or rename individual manifests while the team update is in flight. Keep the architecture stable: browser traffic goes to the Next.js frontend, the frontend calls the Python backend, and the backend is the only component that talks to the OpenAI-compatible inference endpoint.

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
cp app/.env.nvidia.example app/.env.nvidia
# edit app/.env.nvidia locally; never commit it
set -a; source app/.env.nvidia; set +a
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

Run a client-side dry-run if `kubectl` is available:

```sh
kubectl kustomize manifests/sample-app | kubectl apply --dry-run=client --validate=false -f -
```

`kubectl kustomize` does not require cluster credentials. Depending on your `kubectl` version and local kubeconfig, `kubectl apply --dry-run=client` may still attempt API discovery; if that happens, use an authenticated temporary kubeconfig or rely on YAML parse/Kustomize render checks until cluster access is available.

## Deploy with Argo CD / OpenShift GitOps

After the repository is pushed to GitHub and OpenShift GitOps is installed, apply the Argo CD AppProject and Application manifests from an authenticated admin/operator shell:

```sh
oc apply -f gitops/argocd/sample-app-project.yaml
oc apply -f gitops/argocd/sample-app-application.yaml
```

Expected sample-app GitOps shape:

- repo: `https://github.com/dkypuros/austin_rhug_2016.git`
- revision: reviewed release branch or tag
- path: `manifests/sample-app`
- destination namespace: `composer-ai-apps-demo`

Sync should remain manual by default to avoid surprising cluster mutations in the initial harness.

## Validate with Tekton

The Tekton Pipeline expects a workspace named `source` containing a checkout of this repository. Reusable `Task` and `Pipeline` definitions belong under `tekton/`; avoid committing cluster-specific `PipelineRun` credentials or workspaces.

Apply Tekton definitions only when OpenShift Pipelines is installed and live-cluster mutation is intended:

```sh
oc apply -f tekton/tasks/validate-manifests.yaml
oc apply -f tekton/pipelines/hello-world-verify.yaml
# apply any sample-app validation/build tasks or pipelines added by the manifest lane
```

Then create an environment-specific `PipelineRun` that binds a workspace containing this repository checkout.

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
