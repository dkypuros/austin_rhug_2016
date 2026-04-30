#!/usr/bin/env python3
"""
Tiny OpenAI-compatible chat client.

Reads three env vars and nothing else:
  OPENAI_DEFAULT_URL         e.g. https://integrate.api.nvidia.com/v1
                              or  https://vllm-predictor-composer-ai-apps.apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com/v1
  OPENAI_DEFAULT_APIKEY      bearer token for the endpoint
  OPENAI_DEFAULT_MODELNAME   e.g. ibm/granite-3.0-8b-instruct  or  vllm

The same code works against NVIDIA NGC and the in-cluster RHOAI vLLM endpoint,
because both expose the OpenAI chat-completions schema.
"""
import os
import sys
import ssl
import json
import urllib.request
import urllib.error


def main() -> int:
    base = os.environ.get("OPENAI_DEFAULT_URL", "").rstrip("/")
    key = os.environ.get("OPENAI_DEFAULT_APIKEY", "")
    model = os.environ.get("OPENAI_DEFAULT_MODELNAME", "")
    if not (base and key and model):
        print("FAIL: set OPENAI_DEFAULT_URL, OPENAI_DEFAULT_APIKEY, OPENAI_DEFAULT_MODELNAME", file=sys.stderr)
        return 2

    prompt = " ".join(sys.argv[1:]) or "Give me one sentence about Red Hat OpenShift AI."
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 256,
        "temperature": 0.2,
    }).encode("utf-8")

    req = urllib.request.Request(
        base + "/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    ctx = ssl.create_default_context()
    if os.environ.get("OPENAI_INSECURE_TLS") == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:600]
        print(f"FAIL HTTP {e.code}: {detail}", file=sys.stderr)
        return 1

    print(payload["choices"][0]["message"]["content"].strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
