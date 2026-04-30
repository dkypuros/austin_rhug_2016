#!/usr/bin/env python3
"""
Build the Austin RHUG 2026 demo walkthrough deck.

One cover slide, one slide per recorded video (chronological), one closer.
Each video slide carries:
  - the chronological number + title
  - a thumbnail extracted from austin_rhug_obs/frames/
  - a 1-2 sentence beat summary
  - a placeholder "▶  YouTube" caption the user replaces with the real
    URL after upload (clickable link is added by the user in PowerPoint).

Run:
  ../venv/bin/python build_deck.py
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

REPO = Path("/Users/davidkypuros/Documents/Git_ONLINE/austin_rhug_2026")
OBS = Path("/Users/davidkypuros/Documents/Git_ONLINE/austin_rhug_obs")
FRAMES = OBS / "frames"
OUT = Path(__file__).with_name("austin_rhug_2026.pptx")

# Colors
BG = RGBColor(0x0F, 0x14, 0x1E)         # near-black blue
FG = RGBColor(0xF5, 0xF5, 0xF5)
ACCENT = RGBColor(0xEE, 0x00, 0x00)      # Red Hat red
DIM = RGBColor(0x9B, 0xA3, 0xAF)
PILL_BG = RGBColor(0x22, 0x2A, 0x36)

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)  # 16:9


# (number, slug, title, beat) — slug matches frames/<n>_<slug>.jpg
SEGMENTS: list[tuple[int, str, str, str]] = [
    (1,  "ngc-catalog-browse",       "Step 1 — Browse NVIDIA NGC",
        "Open catalog.ngc.nvidia.com to evaluate hosted models. The same client we'll build talks OpenAI-compatible JSON to either NGC or our own cluster."),
    (2,  "terminal-pwd-setup",       "Step 2 — Workspace setup",
        "Fresh terminal, working directory at austin_rhug_2026. Nothing in the harness yet — clean slate."),
    (3,  "harness-security-review",  "Step 3 — Security review of the harness",
        "Claude reviews docs/access.md and .gitignore for secret-handling risk before any code lands. Sets the bar: no .env_* in git, ever."),
    (4,  "claude-code-launch",       "Step 4 — Claude Code launches",
        "Bring up Claude Code (Opus 4.7) inside the project. Plan: build app + tests + manifests against a real RHOAI cluster."),
    (5,  "initial-push-to-github",   "Step 5 — First push to GitHub",
        "Architect/critic review pass, secret-scan green, kustomize/YAML validated. Small initial harness gets committed and pushed."),
    (6,  "github-repo-overview",     "Step 6 — Repo overview",
        "github.com/dkypuros/austin_rhug_2016 — apps/, docs/, gitops/argocd/, tekton/, .env_*.example, harness CLAUDE.md. The skeleton the demo will grow into."),
    (7,  "tag-and-push-v0.1.0",      "Step 7 — Tag v0.1.0 and push",
        "Cut the first release tag and push README + manifests for the sample app. Establishes the GitOps source of truth."),
    (8,  "sample-app-deployed",      "Step 8 — Sample app live on the cluster",
        "Namespace composer-ai-apps-demo, ConfigMap + Secret + Deployment + Route created. End-to-end smoke test returns a real Llama-3.1-8B answer."),
    (9,  "openshift-route-accepted", "Step 9 — OpenShift Route accepted",
        "Verify in the OCP console: Routes → sample-chat → Accepted. The browser-facing URL we'll demo against is live."),
    (10, "local-vs-origin-diff",     "Step 10 — Local vs origin diff",
        "RHOAI Reference docs and the sample app exist locally but aren't on origin/main yet. Surfaces the need to push so the demo is reproducible."),
    (11, "backend-architecture-qa",  "Step 11 — Backend architecture Q&A",
        "Walk through app/server.py: POST /chat, three env vars (URL/APIKEY/MODELNAME), forwards to /chat/completions upstream. The swap surface."),
    (12, "gitops-tekton-verified",   "Step 12 — Argo CD + Tekton verified",
        "Argo CD Application Synced/Healthy, Tekton PipelineRun Succeeded, Deployments rolled out. The pipeline that owns the demo app from now on."),
    (13, "curl-vllm-verification",   "Step 13 — curl the in-cluster vLLM",
        "HTTP 200 from /v1/chat/completions on vllm-composer-ai-apps. Granite 3.0 8B Instruct, served from the GPU node, OpenAI-compatible."),
    (14, "live-frontend-vllm-swap",  "Step 14 — Frontend now on the on-cluster model",
        "Same Next.js page, no code change — backend pill flips to vllm-composer-ai-apps and model: vllm. The promotion moment."),
    (15, "issue-2-followup-prompt",  "Step 15 — Issue #2 follow-up",
        "Plan the next beat: add embeddings + reranking on the same env-var seam. Tracked in GitHub issue #2."),
    (16, "rag-walkthrough-pills",    "Step 16 — RAG walkthrough",
        "Three pills appear: chat (vllm), embed (nv-embedqa-e5-v5), rerank (llama-3.2-nv-rerankqa-1b-v2). Same backend, retrieval lane added."),
    (17, "nvidia-rerank-search",     "Step 17 — Discover the reranker on build.nvidia.com",
        "Two NIM hits for Llama 3.2 NV-RerankQA — the reranker and the embedder. Closes the loop: hosted NIMs available, ready to promote on-cluster too."),
]


def add_solid_bg(slide, color):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.line.fill.background()
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    bg.shadow.inherit = False
    # send to back
    spTree = bg._element.getparent()
    spTree.remove(bg._element)
    spTree.insert(2, bg._element)
    return bg


def textbox(slide, x, y, w, h, text, *, size=18, bold=False, color=FG, align=PP_ALIGN.LEFT, font="Helvetica Neue"):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb


def add_pill(slide, x, y, label, *, fg=FG, bg=PILL_BG, size=11):
    width = Emu(int(Inches(0.05)) + len(label) * 80000)  # rough
    pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, Inches(2.5), Inches(0.32))
    pill.adjustments[0] = 0.5
    pill.line.fill.background()
    pill.fill.solid()
    pill.fill.fore_color.rgb = bg
    tf = pill.text_frame
    tf.margin_left = Inches(0.18)
    tf.margin_right = Inches(0.18)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = label
    run.font.name = "Helvetica Neue"
    run.font.size = Pt(size)
    run.font.color.rgb = fg
    run.font.bold = False
    return pill


def add_cover(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    add_solid_bg(slide, BG)
    # Red bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(2.4), Inches(0.18), Inches(2.6))
    bar.line.fill.background()
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT

    textbox(slide, Inches(1.05), Inches(1.5), Inches(11), Inches(0.5),
            "AUSTIN RHUG · 2026", size=14, bold=True, color=DIM)
    textbox(slide, Inches(1.05), Inches(2.2), Inches(11.5), Inches(2.0),
            "From NVIDIA NGC to Red Hat OpenShift AI", size=44, bold=True, color=FG)
    textbox(slide, Inches(1.05), Inches(3.6), Inches(11.5), Inches(1.5),
            "Evaluate hosted models, then promote your app onto your own GPU\nwith a single GitOps configuration change.",
            size=22, color=DIM)
    textbox(slide, Inches(1.05), Inches(5.5), Inches(11.5), Inches(0.5),
            "17 short videos · click each thumbnail to watch on YouTube",
            size=14, color=DIM)
    textbox(slide, Inches(1.05), Inches(6.4), Inches(11.5), Inches(0.5),
            "github.com/dkypuros/austin_rhug_2016  ·  issues #1 (chat) and #2 (RAG)",
            size=12, color=DIM)


def add_video_slide(prs, n: int, slug: str, title: str, beat: str):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_solid_bg(slide, BG)

    # Step number badge
    badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.6), Inches(0.6), Inches(0.7), Inches(0.7))
    badge.line.fill.background()
    badge.fill.solid()
    badge.fill.fore_color.rgb = ACCENT
    tf = badge.text_frame
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = str(n)
    run.font.name = "Helvetica Neue"
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = FG

    # Title
    textbox(slide, Inches(1.55), Inches(0.55), Inches(11), Inches(0.7),
            title, size=28, bold=True, color=FG)

    # Filename / slug pill
    add_pill(slide, Inches(1.55), Inches(1.32), f"{n}_{slug}.mp4", size=11)

    # Thumbnail (left)
    thumb = FRAMES / f"{n}_{slug}.jpg"
    thumb_x = Inches(0.6)
    thumb_y = Inches(2.1)
    thumb_w = Inches(7.2)
    thumb_h = Inches(4.05)  # 16:9
    if thumb.exists():
        slide.shapes.add_picture(str(thumb), thumb_x, thumb_y, thumb_w, thumb_h)
    else:
        rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, thumb_x, thumb_y, thumb_w, thumb_h)
        rect.line.color.rgb = DIM
        rect.fill.solid()
        rect.fill.fore_color.rgb = PILL_BG
        textbox(slide, thumb_x, thumb_y + Inches(1.7), thumb_w, Inches(0.5),
                "(thumbnail missing)", size=14, color=DIM, align=PP_ALIGN.CENTER)

    # Right column: beat + YouTube placeholder
    right_x = Inches(8.1)
    right_w = Inches(4.8)

    textbox(slide, right_x, Inches(2.1), right_w, Inches(0.4),
            "WHAT YOU'RE WATCHING", size=11, bold=True, color=DIM)
    textbox(slide, right_x, Inches(2.55), right_w, Inches(3.0),
            beat, size=15, color=FG)

    # YouTube placeholder line
    textbox(slide, right_x, Inches(5.6), right_w, Inches(0.4),
            "▶   YouTube link", size=11, bold=True, color=DIM)
    textbox(slide, right_x, Inches(5.95), right_w, Inches(0.5),
            "(paste URL here after upload)", size=13, color=FG)

    # Footer
    textbox(slide, Inches(0.6), Inches(7.05), Inches(8), Inches(0.3),
            f"Austin RHUG · 2026 — Step {n} of {len(SEGMENTS)}",
            size=10, color=DIM)
    textbox(slide, Inches(8.1), Inches(7.05), Inches(4.8), Inches(0.3),
            "github.com/dkypuros/austin_rhug_2016",
            size=10, color=DIM, align=PP_ALIGN.RIGHT)


def add_closer(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_solid_bg(slide, BG)
    textbox(slide, Inches(1.0), Inches(1.5), Inches(11), Inches(0.6),
            "WHAT WE BUILT", size=14, bold=True, color=DIM)
    textbox(slide, Inches(1.0), Inches(2.0), Inches(11.3), Inches(1.2),
            "One client. Two backends. One commit between them.",
            size=36, bold=True, color=FG)

    bullets = [
        "Same OpenAI-compatible client — three env vars choose the backend.",
        "NVIDIA NGC for evaluation; in-cluster vLLM (Granite on RHOAI) for production.",
        "Argo CD owns the swap; same Route, same UI, no code change.",
        "Issue #2 extends the same seam to embeddings + reranking for full RAG.",
    ]
    y = Inches(3.6)
    for line in bullets:
        textbox(slide, Inches(1.2), y, Inches(11), Inches(0.5),
                "•  " + line, size=18, color=FG)
        y += Inches(0.55)

    textbox(slide, Inches(1.0), Inches(6.4), Inches(11.3), Inches(0.5),
            "github.com/dkypuros/austin_rhug_2016 · issues #1 and #2",
            size=14, color=DIM)


def build():
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H

    add_cover(prs)
    for n, slug, title, beat in SEGMENTS:
        add_video_slide(prs, n, slug, title, beat)
    add_closer(prs)

    prs.save(OUT)
    print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes, {len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
