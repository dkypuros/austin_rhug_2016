# app/ — OpenAI-compatible chat backend

Same inference contract, two runtimes. The CLI client (`chat.py`) and HTTP backend (`server.py`) both use the same OpenAI-compatible environment variables, so the demo can move between NVIDIA NGC and on-cluster RHOAI/vLLM by changing configuration rather than code.

Required environment variables:

- `OPENAI_DEFAULT_URL` — OpenAI-compatible base URL, for example `https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/v1`
- `OPENAI_DEFAULT_APIKEY` — bearer token when the endpoint requires one; use a harmless placeholder for this RHOAI vLLM route, and keep real tokens in local env or a Kubernetes Secret, never in git
- `OPENAI_DEFAULT_MODELNAME` — model name sent to `/chat/completions`

Optional environment variables:

- `OPENAI_INSECURE_TLS=1` — skip TLS verification for RHDP/self-signed lab certs only
- `PORT` — HTTP server port, default `8080`
- `CORS_ALLOW_ORIGIN` — comma-separated browser origins allowed to call the backend directly, or `*` for demo-only permissive CORS
- `FRONTEND_ORIGIN` — single-origin alias used when `CORS_ALLOW_ORIGIN` is not set

## Run against NVIDIA NGC

```sh
cp app/.env.nvidia.example app/.env.nvidia
# edit app/.env.nvidia and put your build.nvidia.com key in OPENAI_DEFAULT_APIKEY
set -a; source app/.env.nvidia; set +a
python3 app/chat.py "Give me one sentence about Red Hat OpenShift AI."
```

## Run against the on-cluster RHOAI vLLM endpoint

```sh
cp app/.env.rhoai.example app/.env.rhoai
set -a; source app/.env.rhoai; set +a
python3 app/chat.py "Give me one sentence about Red Hat OpenShift AI."
```

`OPENAI_INSECURE_TLS=1` is only set for the RHDP self-signed cert — drop it in real environments.

## Run the HTTP backend locally

```sh
set -a; source app/.env.nvidia; set +a
PORT=8080 python3 app/server.py
```

Endpoints:

- `GET /healthz` → `{"ok": true}`
- `GET /info` → backend URL, model, chat endpoint, and CORS-enabled status; never returns the API key
- `POST /chat` with `{"prompt":"..."}` → `{"model":"...","reply":"..."}`
- `OPTIONS /chat`, `/info`, `/healthz` → CORS preflight support when `CORS_ALLOW_ORIGIN` or `FRONTEND_ORIGIN` is configured

The backend still serves a minimal `/` smoke-test page, but the sample application UI should use the separate Next.js frontend. If that frontend proxies requests server-side, no CORS variable is required. If browser code calls the backend route directly, set `CORS_ALLOW_ORIGIN` to the frontend route origin.

## Build the backend image

```sh
podman build -t sample-chat-backend:latest -f app/Dockerfile app
```

The image contains only `server.py`; runtime inference credentials remain external environment variables or Kubernetes Secret references.

## Why this shape

The Quarkus LLM router in `composer-ai-apps` reads the same three env vars (`OPENAI_DEFAULT_URL`, `OPENAI_DEFAULT_APIKEY`, `OPENAI_DEFAULT_MODELNAME`). Keeping the demo app on the identical contract means the Act 3 GitOps change is a config update, not a code change.
