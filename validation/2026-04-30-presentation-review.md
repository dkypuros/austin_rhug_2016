# Pre-talk presentation review — 2026-04-30

Two independent reviews ran the day of the talk before the deck was shown
publicly. The deck and supporting artifacts were checked for technical
accuracy, narrative coherence, and honesty about what actually shipped.

- **Reviewer 1**: `oh-my-claudecode:verifier` — coherence and accuracy of the
  cover, SVG context diagrams, code-snippet popups, and 16 voice-track scripts.
- **Reviewer 2**: `oh-my-claudecode:critic` — evidence-based check on whether
  RAG and embeddings actually shipped end-to-end or were only narrated.

Live deck under review: <https://dkypuros.github.io/austin_rhug_2016/presentation/>

## Headline result

**Ship.** The deck is technically accurate, the NVAIE / NGC / RHOAI three-layer
story is consistent across the cover, the big-picture SVG, the closer, and all
16 voice tracks. RAG and embeddings are real; not aspirational. Two small
cleanups described below.

## Reviewer 1 — Verifier

**Verdict**: PASS with 2 nits.

| Severity | Finding | Where | Fix |
|---|---|---|---|
| nit (high embarrassment risk) | GitHub repo slug is `austin_rhug_2016` while the title, kicker, and topbar say `2026`. Audience will see the year mismatch every time the GitHub link is on screen or in the URL. | Cover meta line in `docs/presentation/index.html`; closer; voice tracks 05 and 06. | Rename the repo to `austin_rhug_2026` on GitHub and update references, OR add a parenthetical "(repo slug: 2016)" so the discrepancy reads as deliberate. |
| nit (framing gap) | Slide 16 RAG snippet labeled `(proposed)` in the lightbox header — but Reviewer 2 found the code is shipped. See [Conflict resolved](#conflict-resolved) below. | `index.html` CODE[16] source label. | Remove the `(proposed)` label per Reviewer 2's evidence. |

Reviewer 1 also explicitly confirmed:

- NVAIE / NGC / RHOAI framing is correct everywhere — NVAIE as the umbrella
  entitlement, NGC as the hosted test surface, RHOAI as the on-prem
  destination. Nothing implies the three are interchangeable or mutually
  exclusive.
- Architecture diagrams + model IDs are accurate. `meta/llama-3.1-8b-instruct`
  on the NGC side, `vllm` alias for the in-cluster Granite 3.0 8B Instruct
  served by KServe.
- Slide 17 reranker URL slug `llama-3_2` versus the JSON model id
  `llama-3.2` is correct and self-documented.
- No credentials, internal project names, or sensitive data are exposed.
  The RHDP cluster URL is ephemeral.
- Live deck renders cleanly: HTTP 200, JS/CSS/audio paths intact.

## Reviewer 2 — Critic

**Question**: Did the demo actually ship RAG and embeddings, or did we only
talk about them?

**Verdict**: RAG actually shipped, end-to-end. Issue #2 is already closed.

| Layer | Evidence | Status |
|---|---|---|
| `/rag` endpoint | `app/server.py:286-358` — real HTTP calls to `EMBEDDINGS_URL` and `RERANK_URL`, not stubs. | Live |
| `/rag/info` endpoint | `app/server.py:250-260` — serves live config to the frontend. | Live |
| ConfigMap env vars | `manifests/sample-app/10-configmap-code.yaml:13-16` — `EMBEDDINGS_URL`, `EMBEDDINGS_MODEL`, `RERANK_URL`, `RERANK_MODEL` all populated with real NVIDIA NIM endpoints. | Live |
| Deployment wiring | `manifests/sample-app/30-deployment.yaml:55-72` — all four retrieval env vars injected into the backend container. | Live |
| Frontend UI | `frontend/components/chat-panel.tsx` — three pills (chat / embed / rerank), RAG mode tab, passage textarea, used-passages display, all wired to `/api/rag` and `/api/rag/info`. | Live |
| Frontend proxy | `frontend/app/api/rag/route.ts`, `frontend/app/api/rag/info/route.ts` — Next.js routes proxy to the backend. | Live |
| GitHub issue #2 | `gh issue view 2 --repo dkypuros/austin_rhug_2016` | **CLOSED** |

**Honesty assessment**:

- Voice track 15 (`15_issue-2-followup-prompt.txt`): truthful. Describes the
  planning conversation and the reranker entitlement blocker correctly.
- Voice track 16 (`16_rag-walkthrough-pills.txt`): truthful. Its claim that
  "the RAG flow is live in the UI" is backed by real code at every layer.
- The only stale framing is the `(proposed)` label on the slide 16 code-pill
  lightbox — see below.

## Conflict resolved

The two reviewers gave opposite recommendations on slide 16:

- **Reviewer 1** suggested adding "(proposed — issue #2)" to the slide 16
  beat copy, because the lightbox header already said `(proposed)`.
- **Reviewer 2** found the code is shipped end-to-end and recommended
  removing the `(proposed)` label entirely.

Reviewer 2 wins on evidence: the code is in `app/server.py`, the manifests
wire it through, the frontend renders it, and issue #2 is closed. The
`(proposed)` label is stale.

**Action**: remove the `(proposed)` qualifier from slide 16's CODE entry.

## Ship list

The minimum set of changes to make before the talk:

- [ ] Repo slug: rename to `austin_rhug_2026` on GitHub (or accept the
      `2016` slug as deliberate and acknowledge it on the cover).
- [ ] Slide 16: remove the `(proposed)` qualifier from the code-pill source
      label so it reads `app/server.py` only. Update voice track 16 only if
      it ever said "proposed" — it does not.

Nothing else. The architecture framing, SVG diagrams, model IDs, curl
syntax, GitOps flow, NVAIE/NGC/RHOAI narrative, and the RAG path are all
accurate and honest.
