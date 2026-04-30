# AI Harness Instructions

This file tells AI coding agents how to work in this repository safely.

## Mission

Maintain an OpenShift AI sample-app harness that demonstrates:

- a Next.js App Router frontend under `frontend/` with shadcn-style UI patterns,
- a Python inference backend under `app/` that preserves the OpenAI-compatible chat contract,
- deployable sample-app manifests under `manifests/sample-app/`,
- Argo CD Application/AppProject resources under `gitops/argocd/`,
- Tekton validation/build resources under `tekton/`, and
- safe operational documentation under `docs/` and repository README files.

## Non-negotiable safety rules

1. Never print real tokens, passwords, API keys, kubeconfigs, private keys, or certificate material.
2. Never commit real `.env_*`, `.env`, `.omx/`, `.omc/`, kubeconfig, key, certificate, runtime log, generated agent-state, or local build-output files.
3. Treat local `.env_NVIDIA`, `.env_openshift_lab`, and app-specific env files as sensitive even if they are ignored.
4. Use temporary `KUBECONFIG` for OpenShift tests.
5. Prefer verified TLS and HTTPS downloads. Do not add new `--insecure-skip-tls-verify`, `curl -k`, or unverified HTTP binary-download examples except when explicitly documenting the existing RHDP lab-only TLS limitation.
6. Do not push to GitHub or mutate a live cluster unless the user explicitly requests it.
7. Run validation before claiming completion.

## Expected layout

```text
frontend/                          # Next.js App Router frontend and shadcn-style UI
app/                               # Python backend and CLI helper
manifests/sample-app/              # OpenShift frontend/backend manifests
  README.md
gitops/argocd/                     # Argo CD AppProject/Application resources
tekton/                            # Tekton manifest validation and build coverage
docs/access.md
docs/gh-cli-usage.md
```

Legacy hello-world paths may remain for historical context until the migration is complete, but new sample-app work should prefer `manifests/sample-app/` and sample-app-specific Argo/Tekton resources.

## Backend contract

Do not break these backend semantics without an explicit migration plan:

- `GET /healthz` returns backend health for probes.
- `GET /info` returns safe backend/model metadata for the UI.
- `POST /chat` accepts a prompt payload and forwards to the configured OpenAI-compatible endpoint.
- Runtime configuration stays on:
  - `OPENAI_DEFAULT_URL`
  - `OPENAI_DEFAULT_APIKEY`
  - `OPENAI_DEFAULT_MODELNAME`
  - optional `OPENAI_INSECURE_TLS` for lab-only self-signed TLS.

Never expose `OPENAI_DEFAULT_APIKEY` to frontend/browser-visible env vars. The frontend should call a backend URL or server-side proxy; only the backend should talk to the inference provider.

## Change protocol

- Keep diffs small and reviewable.
- Stay within the file ownership assigned by the active team task.
- Prefer simple Kubernetes/OpenShift YAML over generators for this harness.
- Do not add dependencies unless they are required by the assigned lane or explicitly requested.
- Reuse existing repo patterns before introducing new abstractions.
- Keep Argo CD sync manual unless the user asks for automated sync.
- Keep Tekton resources outside the Argo-managed app path unless the user explicitly changes the architecture.
- If secrets are needed, reference pre-created cluster secrets by name or use Sealed Secrets/External Secrets; never commit inline secret values.
- For Next.js changes, keep browser-exposed env vars free of credentials and run `npm run lint` plus `npm run build` when feasible.

## Verification checklist

Before reporting completion, run the applicable checks and report exact PASS/FAIL evidence:

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

```sh
# Run for every Kustomize directory that exists.
kubectl kustomize apps/hello-world
kubectl kustomize manifests/sample-app
```

```sh
# Run when frontend/package.json exists.
cd frontend
npm install
npm run lint
npm run build
```

```sh
# Static secret-pattern scan; inspect findings before reporting.
python3 - <<'PY'
import re
import subprocess
from pathlib import Path

tracked = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
patterns = [
    re.compile(r'(^|\s)apiKey:\s*(?!replace-me(\s|$))\S+', re.I),
    re.compile(r'(OPENAI_DEFAULT_APIKEY|NVIDIA_API_KEY)\s*=\s*(?!<hidden>)\S+', re.I),
    re.compile(r'(^|\s)(password|token):\s*\S+', re.I),
]
for name in tracked:
    path = Path(name)
    if path.suffix == '.example' or '.example' in path.name:
        continue
    try:
        lines = path.read_text(errors='ignore').splitlines()
    except OSError:
        continue
    for idx, line in enumerate(lines, 1):
        if 're.compile(' in line:
            continue
        if any(p.search(line) for p in patterns):
            print(f'{name}:{idx}:{line}')
PY
```

If a tool is unavailable, a manifest has no `kustomization.yaml`, or client dry-run attempts unreachable API discovery, report that fact and run the next best local/static check. Do not silently skip required evidence.
