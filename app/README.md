# app/ — single-binary chat client

Same code, two backends. Switch by changing three env vars. No code changes between Act 1 (NVIDIA NGC) and Act 3 (on-cluster RHOAI vLLM).

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

## Why this shape

The Quarkus LLM router in `composer-ai-apps` reads the same three env vars (`OPENAI_DEFAULT_URL`, `OPENAI_DEFAULT_APIKEY`, `OPENAI_DEFAULT_MODELNAME`). Keeping the demo app on the identical contract means the Act 3 GitOps change is a config update, not a code change.
