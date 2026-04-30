import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
function read(relativePath) {
  return readFileSync(join(root, relativePath), "utf8");
}

describe("Phase A RAG frontend contract", () => {
  it("defines typed RAG response and info payloads", () => {
    const backend = read("lib/backend.ts");
    assert.match(backend, /export type RagInfo\b/);
    assert.match(backend, /export type RagResponse\b/);
    assert.match(backend, /embed_model\??:/);
    assert.match(backend, /rerank_model\??:/);
    assert.match(backend, /used_passages\??:/);
  });

  it("adds proxy routes for backend /rag and /rag/info", () => {
    assert.equal(existsSync(join(root, "app/api/rag/route.ts")), true, "missing /api/rag route");
    assert.equal(existsSync(join(root, "app/api/rag/info/route.ts")), true, "missing /api/rag/info route");

    const ragRoute = read("app/api/rag/route.ts");
    const ragInfoRoute = read("app/api/rag/info/route.ts");
    assert.match(ragRoute, /export async function POST/);
    assert.match(ragRoute, /proxyJson<[^>]*RagResponse[^>]*>\("\/rag"/);
    assert.match(ragInfoRoute, /export async function GET/);
    assert.match(ragInfoRoute, /proxyJson<[^>]*RagInfo[^>]*>\("\/rag\/info"/);
  });

  it("keeps chat mode available while exposing the RAG controls", () => {
    const panel = read("components/chat-panel.tsx");
    assert.match(panel, /\/api\/chat/);
    assert.match(panel, /\/api\/rag/);
    assert.match(panel, /\/api\/rag\/info/);
    assert.match(panel, /Chat/i);
    assert.match(panel, /RAG/i);
    assert.match(panel, /passages/i);
    assert.match(panel, /used passages/i);
  });
});
