"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { BackendInfo, ChatResponse, RagInfo, RagResponse } from "@/lib/backend";

const DEFAULT_PROMPT = "In one sentence, what is Red Hat OpenShift AI?";
const DEFAULT_PASSAGES = [
  "Red Hat OpenShift AI is a platform for building, training, serving, and monitoring AI-enabled applications on OpenShift.",
  "The Austin RHUG sample keeps chat on the existing vLLM-backed OpenAI-compatible endpoint.",
  "Phase A adds hosted NVIDIA embeddings and reranking as a retrieval lane beside the existing chat flow.",
].join("\n");

type Mode = "chat" | "rag";

function splitPassages(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function displayError(statusCode: number, data: { detail?: string; error?: string }) {
  return `ERROR ${statusCode}: ${data.detail || data.error || "request failed"}`;
}

export function ChatPanel() {
  const [mode, setMode] = React.useState<Mode>("chat");
  const [prompt, setPrompt] = React.useState(DEFAULT_PROMPT);
  const [passages, setPassages] = React.useState(DEFAULT_PASSAGES);
  const [reply, setReply] = React.useState("Reply will appear here.");
  const [usedPassages, setUsedPassages] = React.useState<string[]>([]);
  const [status, setStatus] = React.useState("Ready");
  const [info, setInfo] = React.useState<BackendInfo>({});
  const [ragInfo, setRagInfo] = React.useState<RagInfo>({});
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    let ignore = false;
    fetch("/api/info")
      .then((response) => response.json() as Promise<BackendInfo>)
      .then((data) => {
        if (!ignore) setInfo(data);
      })
      .catch(() => {
        if (!ignore) setStatus("Backend info unavailable");
      });
    fetch("/api/rag/info")
      .then((response) => response.json() as Promise<RagInfo>)
      .then((data) => {
        if (!ignore) setRagInfo(data);
      })
      .catch(() => {
        // The chat path remains usable even if the optional RAG metadata is unavailable.
      });
    return () => {
      ignore = true;
    };
  }, []);

  async function sendChatPrompt(trimmed: string, started: number) {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: trimmed }),
    });
    const data = (await response.json()) as ChatResponse;
    const elapsed = Math.round(performance.now() - started);

    if (!response.ok) {
      setReply(displayError(response.status, data));
      setStatus("Request failed");
      return;
    }

    setReply(data.reply || "(empty response)");
    setStatus(`${data.model || info.model || "model"} · ${elapsed} ms`);
  }

  async function sendRagPrompt(trimmed: string, started: number) {
    const passageList = splitPassages(passages);
    if (passageList.length === 0) {
      setReply("Add at least one passage for RAG mode.");
      setStatus("Passages required");
      return;
    }

    const response = await fetch("/api/rag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: trimmed, passages: passageList, top_k: 10, top_n: 3 }),
    });
    const data = (await response.json()) as RagResponse;
    const elapsed = Math.round(performance.now() - started);

    if (!response.ok) {
      setReply(displayError(response.status, data));
      setStatus("RAG request failed");
      return;
    }

    setReply(data.reply || "(empty response)");
    setUsedPassages(data.used_passages || []);
    setStatus(`${data.model || ragInfo.model || info.model || "model"} · RAG · ${elapsed} ms`);
  }

  async function sendPrompt() {
    const trimmed = prompt.trim();
    if (!trimmed || busy) return;

    setBusy(true);
    setReply("");
    setUsedPassages([]);
    setStatus(mode === "chat" ? "Thinking…" : "Retrieving…");
    const started = performance.now();

    try {
      if (mode === "chat") {
        await sendChatPrompt(trimmed, started);
      } else {
        await sendRagPrompt(trimmed, started);
      }
    } catch (error) {
      setReply(`Fetch failed: ${error instanceof Error ? error.message : String(error)}`);
      setStatus("Network error");
    } finally {
      setBusy(false);
    }
  }

  const chatModel = info.model || ragInfo.model || "loading…";
  const embedModel = ragInfo.embed_model || ragInfo.embeddings_model || "loading…";
  const rerankModel = ragInfo.rerank_model || "loading…";
  const canSend = Boolean(prompt.trim()) && (mode === "chat" || splitPassages(passages).length > 0);

  return (
    <Card className="chat-card">
      <CardHeader>
        <div>
          <p className="eyebrow">Austin RHUG sample</p>
          <h1>OpenShift AI chat</h1>
          <p className="lede">
            A Next.js frontend proxying the existing Python <code>/chat</code> inference contract,
            with an additive hosted-retrieval RAG lane for supplied passages.
          </p>
        </div>
        <div className="status-stack" aria-label="Backend metadata">
          <span className="pill">backend: {info.backend_url || ragInfo.backend_url || "loading…"}</span>
          <span className="pill">chat: {chatModel}</span>
          <span className="pill">embed: {embedModel}</span>
          <span className="pill">rerank: {rerankModel}</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mode-toggle" role="tablist" aria-label="Inference mode">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "chat"}
            className={mode === "chat" ? "mode-tab mode-tab-active" : "mode-tab"}
            onClick={() => setMode("chat")}
            disabled={busy}
          >
            Chat
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "rag"}
            className={mode === "rag" ? "mode-tab mode-tab-active" : "mode-tab"}
            onClick={() => setMode("rag")}
            disabled={busy}
          >
            RAG
          </button>
        </div>
        <label className="field-label" htmlFor="prompt">
          {mode === "chat" ? "Prompt" : "Question"}
        </label>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
              void sendPrompt();
            }
          }}
          placeholder="Ask something about OpenShift AI…"
        />
        {mode === "rag" ? (
          <>
            <label className="field-label field-label-spaced" htmlFor="passages">
              Passages <span className="field-hint">one per line; no upload in Phase A</span>
            </label>
            <textarea
              id="passages"
              className="passages-input"
              value={passages}
              onChange={(event) => setPassages(event.target.value)}
              placeholder="Paste one source passage per line…"
            />
          </>
        ) : null}
        <div className="action-row">
          <Button onClick={() => void sendPrompt()} disabled={busy || !canSend}>
            {busy ? "Sending…" : mode === "chat" ? "Send prompt" : "Run RAG"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setPrompt(DEFAULT_PROMPT);
              setPassages(DEFAULT_PASSAGES);
              setUsedPassages([]);
              setReply("Reply will appear here.");
              setStatus("Ready");
            }}
            disabled={busy}
          >
            Reset
          </Button>
          <span className="request-status" role="status" aria-live="polite">
            {status}
          </span>
        </div>
        <div className="reply-panel" aria-label="Model reply">
          {reply}
        </div>
        {mode === "rag" ? (
          <div className="used-passages" aria-label="Used passages">
            <h2>Used passages</h2>
            {usedPassages.length > 0 ? (
              <ol>
                {usedPassages.map((passage, index) => (
                  <li key={`${index}-${passage.slice(0, 24)}`}>{passage}</li>
                ))}
              </ol>
            ) : (
              <p>No passages used yet.</p>
            )}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
