import { type RagInfo, proxyJson } from "@/lib/backend";

export async function GET(): Promise<Response> {
  return proxyJson<RagInfo>("/rag/info");
}
