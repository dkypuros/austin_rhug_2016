# RHOAI Inference endpoints (reference)

Where it lives in the dashboard: open a row in **Models → Model deployments**, click **Internal and external endpoint**.

Each Model deployment exposes two endpoints:

| Scope | Reachable from | Use it for |
|---|---|---|
| Internal | inside the cluster only | service-to-service traffic from in-cluster apps (the Quarkus router, notebooks, pipelines) — no egress hop |
| External | inside or outside the cluster | local dev, demos, anything off-cluster (curl from your laptop) |

## Live endpoints on this cluster

Deployment: `composer-ai-apps/vllm`

```
Internal: https://vllm.composer-ai-apps.svc.cluster.local
External: https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com
```

The Quarkus LLM router actually points at the **predictor** route, which is a sibling that targets the predictor pod directly:

```
https://vllm-predictor-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/v1
```

All three are OpenAI-compatible vLLM endpoints; they expose `/v1/models`, `/v1/chat/completions`, `/v1/completions`.

## CLI: pull endpoints from the InferenceService

```sh
# Top-level URL
oc -n composer-ai-apps get isvc vllm -o jsonpath='{.status.url}{"\n"}'

# All routes (top-level + predictor)
oc -n composer-ai-apps get route | grep vllm
```

## Smoke test from outside the cluster

```sh
# RHDP self-signed cert → -k for the demo lab only
EXT="https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com"

curl -sk "$EXT/v1/models"

curl -sk "$EXT/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "vllm",
    "messages": [{"role":"user","content":"Reply with the single word: pong"}],
    "max_tokens": 8
  }'
```

`model:` value should match what `/v1/models` returns (in this cluster the served id is `vllm`, configured at deploy time).

## Why both endpoints exist

KServe ships an external `Route` for off-cluster access and an internal `Service` for cluster-local traffic. The demo's *config swap* uses the internal/predictor URL because it gives the in-cluster app the lowest-latency, no-egress path to the model — and it doesn't depend on cluster ingress being reachable.
