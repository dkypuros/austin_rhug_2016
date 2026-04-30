# RHOAI Model deployments (reference)

Where it lives in the dashboard: **Models → Model deployments**, scoped to a project.

A *Model deployment* in the dashboard is a thin UI over a KServe `InferenceService` (single-model serving) or a `ServingRuntime` + `InferenceService` pair (multi-model serving). It binds a model artifact to a serving runtime and exposes inference endpoints.

## Live deployment on this cluster

Project: `composer-ai-apps`

| Field | Value |
|---|---|
| Model deployment name | `vllm` |
| Project | `composer-ai-apps` |
| Serving runtime | Single-model serving enabled (vLLM) |
| API protocol | REST |
| Status | Started |
| Storage | `oci://quay.io/redhat-ai-services/modelcar-catalog:granite-3.0-8b-instruct` |
| Underlying CRD | `serving.kserve.io/v1beta1/InferenceService` |

## Sample InferenceService (reference shape)

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm
  namespace: composer-ai-apps
spec:
  predictor:
    model:
      modelFormat:
        name: vLLM
      runtime: vllm
      storageUri: oci://quay.io/redhat-ai-services/modelcar-catalog:granite-3.0-8b-instruct
```

The OCI modelcar pattern means the model weights ship as a regular container image — no S3/PVC/data-connection wiring needed for this demo.

## CLI: inspect deployments

```sh
oc -n composer-ai-apps get inferenceservice
oc -n composer-ai-apps get isvc vllm -o yaml

# One-liner: name, storageUri, runtime, URL
oc -n composer-ai-apps get inferenceservice -o jsonpath='{range .items[*]}{.metadata.name}{"  storageUri="}{.spec.predictor.model.storageUri}{"  runtime="}{.spec.predictor.model.runtime}{"  url="}{.status.url}{"\n"}{end}'
```

## Pods and route created behind the scenes

```sh
oc -n composer-ai-apps get pods -l serving.kserve.io/inferenceservice=vllm
oc -n composer-ai-apps get route | grep vllm
```

Expected: a single `vllm-predictor-XXXXX` Deployment (the vLLM server pod), plus routes for both the `InferenceService` and its predictor.
