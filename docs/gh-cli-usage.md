# GitHub CLI usage

This project includes `.env_gh_cli.example` as a safe template. Copy it to `.env_gh_cli` for local values and secrets.

## 1. Authenticate

Interactive local login:

```sh
gh auth login --hostname github.com --web
gh auth status
```

Or use a token from `.env_gh_cli` for automation:

```sh
set -a
source .env_gh_cli
set +a
gh auth status --hostname "$GH_HOST"
```

## 2. Point commands at a repository

Edit `.env_gh_cli` so these values are correct:

```sh
GH_REPO_OWNER=dkypuros
GH_REPO=austin_rhug_2016
```

Then load them:

```sh
set -a
source .env_gh_cli
set +a
REPO="$GH_REPO_OWNER/$GH_REPO"
```

## 3. Read repository state

```sh
gh repo view "$REPO" --web
gh repo view "$REPO" --json name,owner,visibility,defaultBranchRef,url
gh issue list --repo "$REPO"
gh pr list --repo "$REPO"
gh release list --repo "$REPO"
```

## 4. Clone or open the repository

```sh
gh repo clone "$REPO"
gh browse --repo "$REPO"
```

## 5. Create issues and PRs

```sh
gh issue create --repo "$REPO" \
  --title "Example task" \
  --body "Created with gh CLI."

gh pr create --repo "$REPO" \
  --base "$GH_DEFAULT_BRANCH" \
  --title "Example PR" \
  --body "Created with gh CLI."
```

## 6. Work with GitHub Actions

```sh
gh run list --repo "$REPO"
gh run view --repo "$REPO" --log
```

## Secret handling

- Commit `.env_gh_cli.example`.
- Do not commit `.env_gh_cli` or token-bearing variants.
- `.gitignore` is configured to hide `.env_gh_cli` while still allowing `.env_gh_cli.example`.
