import { type ChatResponse, proxyJson } from "@/lib/backend";

export async function POST(request: Request): Promise<Response> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "invalid json" }, { status: 400 });
  }

  return proxyJson<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
