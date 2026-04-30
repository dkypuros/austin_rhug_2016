# RHOAI Serving runtimes (reference)

Where it lives in the dashboard: **Settings → Serving runtimes**.

A *Serving runtime* is the engine that hosts a model. RHOAI ships several pre-installed; you pick one when you create a Model deployment.

## Pre-installed runtimes observed on this cluster

| Runtime | Mode | Protocol | Version |
|---|---|---|---|
| OpenVINO Model Server | Single-model | REST | v2025.2.1 |
| **vLLM NVIDIA GPU ServingRuntime for KServe** | Single-model | REST | v0.10.1.1 |
| vLLM AMD GPU ServingRuntime for KServe | Single-model | REST | v0.10.1.1 |
| vLLM Spyre AI Accelerator ServingRuntime for KServe | Single-model | REST | v0.10.1.1 |
| Caikit Standalone ServingRuntime for KServe | Single-model | REST | — |
| vLLM CPU (ppc64le/s390x) ServingRuntime for KServe | Single-model | REST | v0.10.1.1.6 |
| Caikit TGIS ServingRuntime for KServe | Single-model | REST | — |
| Hugging Face Detector ServingRuntime for KServe | Single-model | REST | — |
| OpenVINO Model Server | Multi-model | REST | v2025.2.1 |

The runtime used by the live `vllm` deployment in `composer-ai-apps` is **vLLM NVIDIA GPU ServingRuntime for KServe**, picked up via `spec.predictor.model.runtime: vllm` on the `InferenceService`.

## CLI: list runtimes

```sh
oc get servingruntime,clusterservingruntime -A
oc -n composer-ai-apps get servingruntime
```

## Why it matters for the demo

The runtime is the binding between *the model artifact* (an OCI modelcar in our case) and *the GPU node* (via the runtime's pod spec, tolerations, and resource requests). Choosing `vLLM NVIDIA GPU` is what makes Granite end up on the `worker-gpu` node automatically — no manual node selector on the `InferenceService`.
