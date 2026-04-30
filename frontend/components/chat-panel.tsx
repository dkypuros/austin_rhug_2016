"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { BackendInfo, ChatResponse } from "@/lib/backend";

const DEFAULT_PROMPT = "In one sentence, what is Red Hat OpenShift AI?";

export function ChatPanel() {
  const [prompt, setPrompt] = React.useState(DEFAULT_PROMPT);
  const [reply, setReply] = React.useState("Reply will appear here.");
  const [status, setStatus] = React.useState("Ready");
  const [info, setInfo] = React.useState<BackendInfo>({});
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
    return () => {
      ignore = true;
    };
  }, []);

  async function sendPrompt() {
    const trimmed = prompt.trim();
    if (!trimmed || busy) return;

    setBusy(true);
    setReply("");
    setStatus("Thinking…");
    const started = performance.now();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: trimmed }),
      });
      const data = (await response.json()) as ChatResponse;
      const elapsed = Math.round(performance.now() - started);

      if (!response.ok) {
        setReply(`ERROR ${response.status}: ${data.detail || data.error || "request failed"}`);
        setStatus("Request failed");
        return;
      }

      setReply(data.reply || "(empty response)");
      setStatus(`${data.model || info.model || "model"} · ${elapsed} ms`);
    } catch (error) {
      setReply(`Fetch failed: ${error instanceof Error ? error.message : String(error)}`);
      setStatus("Network error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="chat-card">
      <CardHeader>
        <div>
          <p className="eyebrow">Austin RHUG sample</p>
          <h1>OpenShift AI chat</h1>
          <p className="lede">
            A Next.js frontend proxying the existing Python <code>/chat</code> inference contract.
          </p>
        </div>
        <div className="status-stack" aria-label="Backend metadata">
          <span className="pill">backend: {info.backend_url || "loading…"}</span>
          <span className="pill">model: {info.model || "loading…"}</span>
        </div>
      </CardHeader>
      <CardContent>
        <label className="field-label" htmlFor="prompt">
          Prompt
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
        <div className="action-row">
          <Button onClick={() => void sendPrompt()} disabled={busy || !prompt.trim()}>
            {busy ? "Sending…" : "Send prompt"}
          </Button>
          <Button type="button" variant="secondary" onClick={() => setPrompt(DEFAULT_PROMPT)} disabled={busy}>
            Reset
          </Button>
          <span className="request-status" role="status" aria-live="polite">
            {status}
          </span>
        </div>
        <div className="reply-panel" aria-label="Model reply">
          {reply}
        </div>
      </CardContent>
    </Card>
  );
}
