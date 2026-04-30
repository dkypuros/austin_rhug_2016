import { type BackendInfo, proxyJson } from "@/lib/backend";

export async function GET(): Promise<Response> {
  return proxyJson<BackendInfo>("/info");
}
