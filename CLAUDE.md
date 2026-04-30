# AI Harness Instructions

This file tells AI coding agents how to work in this repository safely.

## Mission

Maintain a minimal OpenShift hello-world harness that demonstrates:

- a deployable app under `apps/hello-world/`,
- an Argo CD Application under `gitops/argocd/`,
- Tekton validation resources under `tekton/`, and
- safe operational documentation under `docs/`.

## Non-negotiable safety rules

1. Never print real tokens, passwords, API keys, kubeconfigs, private keys, or certificate material.
2. Never commit real `.env_*`, `.env`, `.omx/`, `.omc/`, kubeconfig, key, certificate, runtime log, or local agent-state files.
3. Treat local `.env_NVIDIA` and `.env_openshift_lab` values as sensitive even if they are ignored.
4. Use temporary `KUBECONFIG` for OpenShift tests.
5. Prefer verified TLS and HTTPS downloads. Do not add new `--insecure-skip-tls-verify`, `curl -k`, or unverified HTTP binary-download examples.
6. Do not push to GitHub unless the user explicitly requests it.
7. Run validation before claiming completion.

## Expected layout

```text
apps/hello-world/                  # Kustomize-rendered OpenShift workload
gitops/argocd/hello-world-project.yaml
gitops/argocd/hello-world-application.yaml
tekton/tasks/validate-manifests.yaml
tekton/pipelines/hello-world-verify.yaml
docs/access.md
docs/gh-cli-usage.md
```

## Change protocol

- Keep diffs small and reviewable.
- Prefer simple Kubernetes/OpenShift YAML over generators for this harness.
- Do not add dependencies unless the user explicitly asks.
- Use `apps/hello-world` as the single Argo CD source path.
- Keep Argo CD on the dedicated `hello-world` AppProject and immutable/protected release tag `v0.1.0` unless deliberately changed.
- Keep Tekton resources outside the Argo-managed app path unless the user explicitly changes the architecture.
- If secrets are needed later, reference pre-created cluster secrets by name or use Sealed Secrets/External Secrets; never commit inline secret values.

## Verification checklist

Before reporting completion, run the applicable checks:

```sh
python3 - <<'PY'
from pathlib import Path
try:
    import yaml
except Exception as exc:
    raise SystemExit(f'PyYAML unavailable: {exc}')
for path in list(Path('apps').rglob('*.yaml')) + list(Path('gitops').rglob('*.yaml')) + list(Path('tekton').rglob('*.yaml')):
    with path.open() as f:
        list(yaml.safe_load_all(f))
    print(f'parsed {path}')
PY

kubectl kustomize apps/hello-world
```

If a tool is unavailable or client dry-run attempts unreachable API discovery, report that fact and run the next best local/static check.
