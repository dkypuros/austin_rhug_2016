# Austin RHUG 2016 OpenShift GitOps/Tekton Harness

This repository is a minimal, local-first harness for a hello-world OpenShift deployment. It is intended to be pushed later to `https://github.com/dkypuros/austin_rhug_2016.git`, but this task intentionally does **not** push any code.

## What is included

```text
README.md                          # Project harness instructions
apps/hello-world/                  # OpenShift app manifests managed by Argo CD
  kustomization.yaml
  namespace.yaml
  deployment.yaml
  service.yaml
  route.yaml
gitops/argocd/hello-world-project.yaml
gitops/argocd/hello-world-application.yaml
tekton/tasks/validate-manifests.yaml
tekton/pipelines/hello-world-verify.yaml
docs/access.md                     # Access runbook for GitHub/NVIDIA/OpenShift
docs/gh-cli-usage.md               # GitHub CLI quick reference
.env_gh_cli.example                # Safe GitHub CLI env template
.env_NVIDIA.example                # Safe NVIDIA env template
.env_openshift_lab.example         # Safe OpenShift/RHDP env template
.gitignore                         # Secret/runtime ignore policy
CLAUDE.md                          # AI-agent harness instructions
```

## Security defaults

- Do not commit real `.env_*`, `.env`, `.omx/`, `.omc/`, kubeconfig, key, certificate, token, or runtime log files.
- `.gitignore` is intentionally broad because this repo contains deployment examples and local AI-agent runtime state.
- Do not print secret values in terminal output, docs, commits, issues, or pull requests.
- Use temporary `KUBECONFIG` files for OpenShift validation.
- Use pre-created cluster secrets referenced by name, Sealed Secrets, or External Secrets for future secret delivery. Never commit inline secret values.
- The hello-world workload uses an unprivileged nginx image and restricted-friendly pod/container security settings.

## Local prerequisites

Recommended tools:

- `gh` for GitHub CLI workflows
- `kubectl` or `oc` for manifest validation
- OpenShift GitOps/Argo CD installed in the target cluster for `Application` sync
- OpenShift Pipelines/Tekton installed in the target cluster for pipeline execution

See `docs/access.md` for environment-file and cluster access patterns. Keep real environment files local and ignored.

## Validate locally

Render the app manifests:

```sh
kubectl kustomize apps/hello-world
```

Run a client-side dry-run if `kubectl` is available:

```sh
kubectl kustomize apps/hello-world | kubectl apply --dry-run=client --validate=false -f -
```

`kubectl kustomize` does not require cluster credentials. Depending on your `kubectl` version and local kubeconfig, `kubectl apply --dry-run=client` may still attempt API discovery; if that happens, use an authenticated temporary kubeconfig or rely on the YAML parse and kustomize render checks until cluster access is available.

## Deploy with Argo CD / OpenShift GitOps

After the repository is pushed to GitHub and OpenShift GitOps is installed, apply the Argo CD AppProject and Application manifests from an authenticated admin/operator shell:

```sh
oc apply -f gitops/argocd/hello-world-project.yaml
oc apply -f gitops/argocd/hello-world-application.yaml
```

The Application points Argo CD at:

- repo: `https://github.com/dkypuros/austin_rhug_2016.git`
- revision: `v0.1.0`
- path: `apps/hello-world`
- destination namespace: `hello-world`

Sync is manual by default to avoid surprising cluster mutations in the initial harness. The `v0.1.0` tag should be created after the first reviewed commit and treated as immutable/protected.

## Validate with Tekton

The Tekton Pipeline expects a workspace named `source` containing a checkout of this repository. The initial harness commits only reusable `Task` and `Pipeline` definitions; it does not commit a `PipelineRun` because workspace binding and credentials are cluster-specific.

Apply the Tekton definitions when OpenShift Pipelines is installed:

```sh
oc apply -f tekton/tasks/validate-manifests.yaml
oc apply -f tekton/pipelines/hello-world-verify.yaml
```

Then create an environment-specific `PipelineRun` that binds a workspace containing this repository checkout.

## GitHub workflow

The target repository has been created as a private repo:

```text
https://github.com/dkypuros/austin_rhug_2016
```

Before pushing:

1. Re-run the secret scan and manifest validation.
2. Confirm `git status` does not include real `.env_*`, `.omx/`, `.omc/`, kubeconfig, or key/cert files.
3. Commit with a Lore-style commit message if/when this directory is initialized as a git repository.
4. Push only after explicit user instruction.
