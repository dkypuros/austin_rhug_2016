# Sample chat app — in-cluster

Deploys `app/server.py` on the RHOAI cluster in a fresh namespace `composer-ai-apps-demo` (does not touch the live `composer-ai-apps` workloads).

Three env vars on the Deployment select the LLM backend — exactly the same contract the demo plan uses to promote between NVIDIA NGC and the on-cluster vLLM endpoint:

```
OPENAI_DEFAULT_URL        e.g. https://integrate.api.nvidia.com/v1
OPENAI_DEFAULT_APIKEY     from Secret llm-credentials
OPENAI_DEFAULT_MODELNAME  e.g. meta/llama-3.1-8b-instruct  (Act 1)
                          or  vllm                          (Act 3)
```

## Apply

```sh
cd /Users/davidkypuros/Documents/Git_ONLINE/austin_rhug_2026
set -a; source .env_openshift_lab; set +a
export KUBECONFIG="$(mktemp -d)/kubeconfig"
oc login "$OPENSHIFT_API_URL" -u "$OPENSHIFT_ADMIN_USER" -p "$OPENSHIFT_ADMIN_PASSWORD" --insecure-skip-tls-verify=true

# Namespace
oc apply -f manifests/sample-app/00-namespace.yaml

# Code ConfigMap (renders server.py from app/server.py at apply time)
oc -n composer-ai-apps-demo create configmap sample-chat-code \
  --from-file=server.py=app/server.py \
  --dry-run=client -o yaml | oc apply -f -

# API key Secret (NVIDIA NGC for Act 1)
set -a; source .env_NVIDIA; set +a
oc -n composer-ai-apps-demo create secret generic llm-credentials \
  --from-literal=apiKey="$NVIDIA_API_KEY" \
  --dry-run=client -o yaml | oc apply -f -

# Deployment + Service + Route
oc apply -f manifests/sample-app/30-deployment.yaml
oc apply -f manifests/sample-app/40-service-route.yaml

oc -n composer-ai-apps-demo rollout status deploy/sample-chat
ROUTE="https://$(oc -n composer-ai-apps-demo get route sample-chat -o jsonpath='{.spec.host}')"
echo "$ROUTE"
curl -s "$ROUTE/" ; echo
curl -s -X POST "$ROUTE/chat" -H 'Content-Type: application/json' \
  -d '{"prompt":"In one sentence, what is Red Hat OpenShift AI?"}'
```

## Promote to the on-cluster vLLM endpoint (Act 3)

Patch the Deployment env (or, in the GitOps version, commit the same change to the manifest):

```sh
oc -n composer-ai-apps-demo set env deploy/sample-chat \
  OPENAI_DEFAULT_URL=https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/v1 \
  OPENAI_DEFAULT_MODELNAME=vllm \
  OPENAI_INSECURE_TLS=1
oc -n composer-ai-apps-demo set env deploy/sample-chat --from=secret/llm-credentials  # re-bind apiKey
```

Update the Secret to a placeholder value (the in-cluster vLLM doesn't enforce auth in this lab):

```sh
oc -n composer-ai-apps-demo create secret generic llm-credentials \
  --from-literal=apiKey=abc123 --dry-run=client -o yaml | oc apply -f -
```

Same Route, same `/chat` endpoint — now served by Granite on the cluster.

## Files

| File | Purpose |
|---|---|
| `00-namespace.yaml` | dedicated namespace, isolated from `composer-ai-apps` |
| `10-configmap-code.yaml` | placeholder; the real ConfigMap is created from `app/server.py` via `oc create cm --from-file` |
| `20-secret.yaml.example` | template for `llm-credentials` Secret (real one created at apply time, never committed) |
| `30-deployment.yaml` | runs `python3 /opt/app/server.py` on `ubi9/python-311`, mounts the ConfigMap |
| `40-service-route.yaml` | ClusterIP Service + edge-terminated Route |
