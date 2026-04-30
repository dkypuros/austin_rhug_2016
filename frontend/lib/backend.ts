export type BackendInfo = {
  backend_url?: string;
  model?: string;
};

export type ChatResponse = {
  model?: string;
  reply?: string;
  error?: string;
  detail?: string;
};

export const DEFAULT_BACKEND_URL = "http://localhost:8080";

export function getBackendUrl(): string {
  return (process.env.BACKEND_URL || DEFAULT_BACKEND_URL).replace(/\/$/, "");
}

export async function proxyJson<T>(path: string, init?: RequestInit): Promise<Response> {
  const upstream = await fetch(`${getBackendUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  const payload = (await upstream.json()) as T;
  return Response.json(payload, { status: upstream.status });
}
