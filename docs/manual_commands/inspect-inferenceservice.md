# Inspect a deployed model on Red Hat OpenShift AI

How to identify the model behind a RHOAI "Model deployment" (KServe `InferenceService`).

Run these blocks top-to-bottom from a fresh terminal. Each block is self-contained and copy-pasteable.

## 1. Go to the project folder and load the lab env

```sh
cd /Users/davidkypuros/Documents/Git_ONLINE/austin_rhug_2026
set -a; source .env_openshift_lab; set +a
```

## 2. Log in with a temp kubeconfig (keeps ~/.kube/config untouched)

```sh
export KUBECONFIG="$(mktemp -d)/kubeconfig"
oc login "$OPENSHIFT_API_URL" \
  -u "$OPENSHIFT_ADMIN_USER" -p "$OPENSHIFT_ADMIN_PASSWORD" \
  --insecure-skip-tls-verify=true
oc whoami
oc whoami --show-server
```

If `oc whoami --show-server` does **not** match `$OPENSHIFT_API_URL`, your shell is using a stale kubeconfig — re-export `KUBECONFIG` and re-run `oc login`.

## 3. List InferenceServices in the project

```sh
oc -n composer-ai-apps get isvc
```

## 4. One-liner: pull the key fields from every InferenceService

```sh
oc -n composer-ai-apps get inferenceservice -o jsonpath='{range .items[*]}{.metadata.name}{"\n  storageUri: "}{.spec.predictor.model.storageUri}{"\n  modelFormat: "}{.spec.predictor.model.modelFormat.name}{"\n  runtime: "}{.spec.predictor.model.runtime}{"\n  args: "}{.spec.predictor.model.args}{"\n  url: "}{.status.url}{"\n"}{end}'
```

## 5. Full YAML for a single InferenceService

```sh
oc -n composer-ai-apps get inferenceservice vllm -o yaml
```

## Where the model identity lives

`.spec.predictor.model.storageUri` — for `composer-ai-apps/vllm` this resolved to:

```
oci://quay.io/redhat-ai-services/modelcar-catalog:granite-3.0-8b-instruct
```

i.e. IBM Granite 3.0 8B Instruct, served via vLLM as a KServe modelcar OCI image.

## Troubleshooting

- `Unable to connect to the server: dial tcp: lookup api.cluster-XXXX...: no such host`
  → your kubeconfig points at an old/expired RHDP sandbox. Re-run **step 2** to reset `KUBECONFIG` and log into the current lab from `.env_openshift_lab`.
- `Unauthorized` / `x509`: lab credentials rotated or cert changed; confirm `.env_openshift_lab` matches the current RHDP order.
