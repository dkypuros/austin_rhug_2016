# Access runbook: GitHub, NVIDIA, and OpenShift

This runbook is written for a fresh AI/chat window that has no memory of the setup. Start here when you need to test access to GitHub, NVIDIA, or the RHDP/OpenShift lab from this folder.

## Repository/folder context

Expected working directory:

```sh
cd /Users/davidkypuros/Documents/Git_ONLINE/austin_rhug_2026
```

Important files:

| File | Purpose | Safe to commit? |
| --- | --- | --- |
| `.env_gh_cli.example` | Template for GitHub CLI settings | Yes |
| `.env_gh_cli` | Local GitHub CLI settings/secrets | No |
| `.env_NVIDIA.example` | Template for NVIDIA API settings | Yes |
| `.env_NVIDIA` | Local NVIDIA API key/settings | No |
| `.env_openshift_lab.example` | Template for OpenShift lab settings | Yes |
| `.env_openshift_lab` | Local RHDP/OpenShift URLs and credentials | No |
| `.gitignore` | Keeps real `.env*` secret files out of git | Yes |

The real `.env_*`, generic `.env*`, kubeconfig, key/certificate, and local agent-runtime files are intentionally ignored by `.gitignore`. Do not print their secret values into logs, documentation, commits, issues, or PRs.

## General pattern for loading env files

Use this pattern in `zsh`/`bash` whenever a test needs environment variables:

```sh
set -a
source .env_NAME
set +a
```

Example:

```sh
set -a
source .env_NVIDIA
set +a
```

Check that a file parses without printing secret values:

```sh
zsh -n .env_gh_cli
zsh -n .env_NVIDIA
zsh -n .env_openshift_lab
```

## Secret handling rules for future AI agents

1. Never echo full token/password values.
2. It is okay to print variable names and non-secret endpoint URLs.
3. Prefer read-only validation commands.
4. For OpenShift, use a temporary `KUBECONFIG` so the user's default kubeconfig is not modified.
5. If a command fails, report the error/status without dumping environment variables.
6. Commit only `*.example` files and docs; do not commit real `.env_*` files.

---

# 1. GitHub CLI access

## Files and variables

Real local file:

```sh
.env_gh_cli
```

Template:

```sh
.env_gh_cli.example
```

Expected variables:

```sh
GH_HOST=github.com
GH_REPO_OWNER=dkypuros
GH_REPO=austin_rhug_2016
GH_DEFAULT_BRANCH=main
```

Optional automation variables may exist, but local interactive `gh auth login` is preferred:

```sh
GH_TOKEN=<hidden>
GITHUB_TOKEN=<hidden>
```

## Load GitHub environment

```sh
set -a
source .env_gh_cli
set +a

REPO="$GH_REPO_OWNER/$GH_REPO"
echo "Testing GitHub repo: $REPO"
```

## Test account auth

```sh
gh auth status --hostname "$GH_HOST"
gh api user --jq '{login, name, html_url, id}'
```

Expected from the current setup:

- login: `dkypuros`
- profile: `https://github.com/dkypuros`

## List accessible repos

Use this when you do not know which repo name to test:

```sh
gh repo list "$GH_REPO_OWNER" --limit 20 --json name,visibility,isPrivate,updatedAt \
  --jq '.[] | {name, visibility, isPrivate, updatedAt}'
```

## Test a specific repo

```sh
gh repo view "$REPO" --json name,owner,visibility,defaultBranchRef,url
gh issue list --repo "$REPO" --limit 10
gh pr list --repo "$REPO" --limit 10
gh run list --repo "$REPO" --limit 10
```

If `gh repo view "$REPO"` fails with “Could not resolve to a Repository,” the token may still be valid but `GH_REPO` is wrong or the repo does not exist. Run the repo list command above and update `.env_gh_cli`.

## Useful GitHub commands

```sh
# Open repo in browser
gh browse --repo "$REPO"

# Clone repo
gh repo clone "$REPO"

# Create an issue, if explicitly requested
gh issue create --repo "$REPO" --title "Example task" --body "Created with gh CLI."

# Create a PR from the current git branch, if inside a git repo
gh pr create --repo "$REPO" --base "$GH_DEFAULT_BRANCH" --title "Example PR" --body "Created with gh CLI."
```

---

# 2. NVIDIA API access

## Files and variables

Real local file:

```sh
.env_NVIDIA
```

Template:

```sh
.env_NVIDIA.example
```

Expected variables:

```sh
NVIDIA_API_KEY=<hidden>
NGC_API_KEY=$NVIDIA_API_KEY
NVAPI_KEY=$NVIDIA_API_KEY
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

## Load NVIDIA environment

```sh
set -a
source .env_NVIDIA
set +a
```

## Test the key with curl

Read-only model listing:

```sh
curl -sS "$NVIDIA_BASE_URL/models" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Accept: application/json"
```

If `jq` is installed, summarize without printing too much output:

```sh
curl -sS "$NVIDIA_BASE_URL/models" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Accept: application/json" \
  | jq '{model_count: (.data | length), first_models: [.data[0:10][].id]}'
```

## Test the key with Python

Use this version when you want a clean pass/fail result:

```sh
python3 - <<'PY'
import json, os, sys, urllib.request, urllib.error
base = os.environ.get('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1').rstrip('/')
key = os.environ.get('NVIDIA_API_KEY')
if not key:
    print('FAIL: NVIDIA_API_KEY is not set')
    sys.exit(1)
req = urllib.request.Request(
    base + '/models',
    headers={'Authorization': 'Bearer ' + key, 'Accept': 'application/json'},
    method='GET',
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
        models = payload.get('data', [])
        print(f'PASS: HTTP {resp.status}; key accepted; {len(models)} models visible')
        for model in models[:10]:
            print('-', model.get('id'))
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace')[:500]
    print(f'FAIL: HTTP {e.code}: {body}')
    sys.exit(1)
except Exception as e:
    print('FAIL:', type(e).__name__, str(e))
    sys.exit(1)
PY
```

Expected result from the current setup at the time it was created:

- HTTP status: `200`
- Key accepted
- Model list returned

---

# 3. OpenShift/RHDP lab access

## Files and variables

Real local file:

```sh
.env_openshift_lab
```

Template:

```sh
.env_openshift_lab.example
```

Expected variables:

```sh
OPENSHIFT_LAB_NAME="Composer AI"
OPENSHIFT_LAB_ID="nhsxz"
OPENSHIFT_CLUSTER_NAME="cluster-nhsxz"
OPENSHIFT_BASE_DOMAIN="nhsxz.sandbox1513.opentlc.com"
OPENSHIFT_CLUSTER_DOMAIN="cluster-nhsxz.nhsxz.sandbox1513.opentlc.com"
OPENSHIFT_APPS_DOMAIN="apps.cluster-nhsxz.nhsxz.sandbox1513.opentlc.com"
OPENSHIFT_CONSOLE_URL=<console-url>
OPENSHIFT_API_URL=<api-url>
OPENSHIFT_GITOPS_ARGOCD_URL=<argocd-url>
OPENSHIFT_OC_CLIENT_URL=<https-oc-download-url>
OPENSHIFT_AUTH_PROVIDER="htpasswd"
OPENSHIFT_ADMIN_USER="admin"
OPENSHIFT_ADMIN_PASSWORD=<hidden>
OPENSHIFT_USER="user1"
OPENSHIFT_USER_PASSWORD=<hidden>
OPENSHIFT_STOP_AT_UTC="2026-04-30T06:15:00Z"
OPENSHIFT_EXPIRE_AT_UTC="2026-04-30T19:26:00Z"
```

Important: this RHDP environment is ephemeral. The original notice said it stops at `2026-04-30T06:15:00Z` and expires/deletes at `2026-04-30T19:26:00Z`. If testing after those timestamps, failures may simply mean the lab has expired.

## Load OpenShift environment

```sh
set -a
source .env_openshift_lab
set +a
```

## Test endpoints without logging in

```sh
python3 - <<'PY'
import os, ssl, urllib.request, urllib.error
urls = [
    ('console', os.environ['OPENSHIFT_CONSOLE_URL']),
    ('api-readyz', os.environ['OPENSHIFT_API_URL'].rstrip('/') + '/readyz'),
    ('gitops', os.environ['OPENSHIFT_GITOPS_ARGOCD_URL']),
]
ctx = ssl.create_default_context()
for name, url in urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'ocp-lab-check/1.0'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
            print(f'{name}: HTTP {r.status}')
    except urllib.error.HTTPError as e:
        print(f'{name}: HTTP {e.code}')
    except Exception as e:
        print(f'{name}: FAIL {type(e).__name__}: {e}')
PY
```

Expected when the lab is alive:

```text
console: HTTP 200
api-readyz: HTTP 200
gitops: HTTP 200
```

## Find or install `oc`

Use existing `oc` if available:

```sh
command -v oc
oc version --client=true
```

If missing, download the lab-provided client into a temporary directory. Prefer HTTPS URLs and verify checksums when the lab provides them:

```sh
TMPDIR_OC="$(mktemp -d)"
curl -fsSL "$OPENSHIFT_OC_CLIENT_URL" -o "$TMPDIR_OC/oc.tar.gz"
tar -xzf "$TMPDIR_OC/oc.tar.gz" -C "$TMPDIR_OC" oc
chmod +x "$TMPDIR_OC/oc"
OC_BIN="$TMPDIR_OC/oc"
"$OC_BIN" version --client=true
```

If `oc` already exists:

```sh
OC_BIN="$(command -v oc)"
```

## Test admin login safely

Use a temporary kubeconfig so this test does not alter `~/.kube/config`:

```sh
TMPDIR_KUBE="$(mktemp -d)"
export KUBECONFIG="$TMPDIR_KUBE/kubeconfig"
OC_BIN="${OC_BIN:-$(command -v oc)}"
OC_TLS_ARGS=()
if [ -n "${OPENSHIFT_CA_CERT:-}" ]; then
  OC_TLS_ARGS=(--certificate-authority "$OPENSHIFT_CA_CERT")
fi

"$OC_BIN" login "$OPENSHIFT_API_URL" \
  -u "$OPENSHIFT_ADMIN_USER" \
  -p "$OPENSHIFT_ADMIN_PASSWORD" \
  "${OC_TLS_ARGS[@]}"

"$OC_BIN" whoami
"$OC_BIN" whoami --show-server
"$OC_BIN" get nodes
"$OC_BIN" get co
"$OC_BIN" get projects | head
```

Expected when the lab is healthy:

- `oc whoami` returns `admin`
- nodes are `Ready`
- cluster operators report healthy/available

## Test normal user login safely

Use the same temporary `KUBECONFIG` or create a new one:

```sh
"$OC_BIN" login "$OPENSHIFT_API_URL" \
  -u "$OPENSHIFT_USER" \
  -p "$OPENSHIFT_USER_PASSWORD" \
  "${OC_TLS_ARGS[@]}"

"$OC_BIN" whoami
"$OC_BIN" get projects
```

Expected when the lab is healthy:

- `oc whoami` returns `user1`
- normal user has limited project visibility

## One-shot OpenShift validation script

This script performs endpoint checks, admin login, read-only cluster checks, and normal-user login. It uses a temporary kubeconfig and removes it afterward.

```sh
set -euo pipefail
set -a; source .env_openshift_lab; set +a

TMPDIR_OC="$(mktemp -d)"
cleanup() { rm -rf "$TMPDIR_OC"; }
trap cleanup EXIT
export KUBECONFIG="$TMPDIR_OC/kubeconfig"
OC_TLS_ARGS=()
if [ -n "${OPENSHIFT_CA_CERT:-}" ]; then
  OC_TLS_ARGS=(--certificate-authority "$OPENSHIFT_CA_CERT")
fi

if command -v oc >/dev/null 2>&1; then
  OC_BIN="$(command -v oc)"
else
  curl -fsSL "$OPENSHIFT_OC_CLIENT_URL" -o "$TMPDIR_OC/oc.tar.gz"
  tar -xzf "$TMPDIR_OC/oc.tar.gz" -C "$TMPDIR_OC" oc
  chmod +x "$TMPDIR_OC/oc"
  OC_BIN="$TMPDIR_OC/oc"
fi

"$OC_BIN" login "$OPENSHIFT_API_URL" \
  -u "$OPENSHIFT_ADMIN_USER" \
  -p "$OPENSHIFT_ADMIN_PASSWORD" \
  "${OC_TLS_ARGS[@]}" >/dev/null

echo "admin whoami: $("$OC_BIN" whoami)"
"$OC_BIN" get nodes
"$OC_BIN" get co --no-headers | awk 'BEGIN{bad=0} {if ($3!="True" || $4!="False" || $5!="False") bad++; total++} END{print "cluster operators: total="total" nonhealthy="bad}'

"$OC_BIN" login "$OPENSHIFT_API_URL" \
  -u "$OPENSHIFT_USER" \
  -p "$OPENSHIFT_USER_PASSWORD" \
  "${OC_TLS_ARGS[@]}" >/dev/null

echo "user whoami: $("$OC_BIN" whoami)"
echo "visible projects: $("$OC_BIN" get projects --no-headers 2>/dev/null | wc -l | tr -d ' ')"

echo "PASS: OpenShift lab credentials and endpoints are usable"
```

---

# 4. Full access test checklist

From a fresh window, run this sequence:

```sh
cd /Users/davidkypuros/Documents/Git_ONLINE/austin_rhug_2026

# Confirm files exist without printing secrets
ls -la .env_gh_cli .env_gh_cli.example \
       .env_NVIDIA .env_NVIDIA.example \
       .env_openshift_lab .env_openshift_lab.example

zsh -n .env_gh_cli
zsh -n .env_NVIDIA
zsh -n .env_openshift_lab
```

Then test each service:

```sh
# GitHub
set -a; source .env_gh_cli; set +a
REPO="$GH_REPO_OWNER/$GH_REPO"
gh auth status --hostname "$GH_HOST"
gh api user --jq '{login, name, html_url, id}'
gh repo view "$REPO" --json name,owner,visibility,url || gh repo list "$GH_REPO_OWNER" --limit 20

# NVIDIA
set -a; source .env_NVIDIA; set +a
curl -sS "$NVIDIA_BASE_URL/models" -H "Authorization: Bearer $NVIDIA_API_KEY" -H "Accept: application/json" | head -c 500; echo

# OpenShift
set -a; source .env_openshift_lab; set +a
curl -sS "$OPENSHIFT_API_URL/readyz" | head
```

For deeper OpenShift testing, use the one-shot validation script above.

## Known last-good checks

These were the last successful checks when the env files were created:

- GitHub CLI authenticated as `dkypuros` and could list public/private repos.
- NVIDIA API returned `HTTP 200` from `/models` and listed models.
- OpenShift endpoints returned `HTTP 200`; admin and `user1` logins worked; nodes were Ready; 33 cluster operators had 0 nonhealthy.

If future checks fail, first check whether credentials rotated, the target GitHub repo name changed, network/VPN access is required, or the RHDP lab expired.
