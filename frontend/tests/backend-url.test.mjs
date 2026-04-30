import assert from "node:assert/strict";
import { describe, it } from "node:test";

const DEFAULT_BACKEND_URL = "http://localhost:8080";
function normalizeBackendUrl(value) {
  return (value || DEFAULT_BACKEND_URL).replace(/\/$/, "");
}

describe("backend URL normalization", () => {
  it("uses the local Python backend by default", () => {
    assert.equal(normalizeBackendUrl(""), DEFAULT_BACKEND_URL);
  });

  it("removes one trailing slash from configured service URLs", () => {
    assert.equal(normalizeBackendUrl("http://sample-chat-backend:8080/"), "http://sample-chat-backend:8080");
  });
});
