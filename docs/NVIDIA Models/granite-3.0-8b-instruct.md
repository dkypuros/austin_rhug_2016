# IBM Granite 3.0 8B Instruct via NVIDIA NIM API

The same model deployed in our RHOAI cluster (`composer-ai-apps/vllm` →
`oci://quay.io/redhat-ai-services/modelcar-catalog:granite-3.0-8b-instruct`)
is also hosted by NVIDIA at `https://integrate.api.nvidia.com/v1` as
`ibm/granite-3.0-8b-instruct`. Both expose an OpenAI-compatible API, so the
same request body works against either — just swap base URL + auth.

## Granite models available on NVIDIA NIM

- `ibm/granite-3.0-8b-instruct`
- `ibm/granite-3.0-3b-a800m-instruct`
- `ibm/granite-34b-code-instruct`
- `ibm/granite-8b-code-instruct`

## 1. Load the NVIDIA env

```sh
cd /Users/davidkypuros/Documents/Git_ONLINE/austin_rhug_2026
set -a; source .env_NVIDIA; set +a
```

Expected vars: `NVIDIA_API_KEY`, `NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1`.

## 2. Confirm the model is visible to your key

```sh
curl -sS "$NVIDIA_BASE_URL/models" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Accept: application/json" \
  | python3 -c "import json,sys; ids=[m['id'] for m in json.load(sys.stdin)['data']]; print('\n'.join(i for i in ids if 'granite' in i.lower()))"
```

## 3. Chat completion (curl)

```sh
curl -sS "$NVIDIA_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ibm/granite-3.0-8b-instruct",
    "messages": [
      {"role": "system", "content": "You are a concise assistant."},
      {"role": "user",   "content": "Give me one sentence about Red Hat OpenShift AI."}
    ],
    "temperature": 0.2,
    "max_tokens": 128
  }'
```

## 4. Chat completion (Python, OpenAI SDK)

```sh
python3 - <<'PY'
import os
from openai import OpenAI  # pip install openai
client = OpenAI(
    base_url=os.environ["NVIDIA_BASE_URL"],
    api_key=os.environ["NVIDIA_API_KEY"],
)
resp = client.chat.completions.create(
    model="ibm/granite-3.0-8b-instruct",
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user",   "content": "Give me one sentence about Red Hat OpenShift AI."},
    ],
    temperature=0.2,
    max_tokens=128,
)
print(resp.choices[0].message.content)
PY
```

## 5. A/B against the in-cluster RHOAI vLLM endpoint

The KServe `vllm` InferenceService exposes the OpenAI API too. Swap base URL
and (if required) auth — request body is identical.

```sh
# In-cluster RHOAI URL (from `oc get isvc -n composer-ai-apps`)
RHOAI_URL="https://vllm-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com"

# vLLM exposes models at /v1/* — list them
curl -sk "$RHOAI_URL/v1/models"

# Same prompt, same body, just different base URL + (optional) bearer token
curl -sk "$RHOAI_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "granite-3.0-8b-instruct",
    "messages": [{"role":"user","content":"Give me one sentence about Red Hat OpenShift AI."}],
    "max_tokens": 128
  }'
```

Notes:
- The in-cluster `model` field is the served model name reported by `/v1/models` (often `granite-3.0-8b-instruct`, *without* the `ibm/` prefix). The NVIDIA-hosted name is `ibm/granite-3.0-8b-instruct`.
- If the KServe route enforces auth, add `-H "Authorization: Bearer $(oc whoami -t)"` or the configured token.
- `-k` skips TLS verification for the RHDP self-signed cert; remove it in real environments.

## Known gotcha: 404 "Function … Not found for account"

```
{"status":404,"title":"Not Found","detail":"Function '...': Not found for account '...'"}
```

This means the model **is listed** in `/v1/models` for your key but the
account is **not entitled** to invoke that specific NIM function. Listing on
`build.nvidia.com` / `/v1/models` ≠ runtime access. Fixes:

- Open the model card on `https://build.nvidia.com/ibm/granite-3-0-8b-instruct` and click "Get API Key" / "Try API" while logged in with the same account that owns `NVIDIA_API_KEY` — this provisions the function for your account.
- Or generate a fresh personal key from `build.nvidia.com` (NGC personal keys and `build.nvidia.com` keys are not interchangeable for all NIM functions).
- Confirm the active account: `curl -sS https://integrate.api.nvidia.com/v1/models -H "Authorization: Bearer $NVIDIA_API_KEY" | head -c 200` and check the model is present, then retry the chat call.

If only `/v1/models` works but every `/v1/chat/completions` call 404s, the key
is read-only / unentitled — regenerate it.

## Secret handling

- Never echo `NVIDIA_API_KEY`. Only `.env_NVIDIA.example` is committed; `.env_NVIDIA` is gitignored.
