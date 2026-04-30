import { ChatPanel } from "@/components/chat-panel";

export default function Home() {
  return (
    <main>
      <div className="shell">
        <div className="hero-copy">
          <span className="badge">GitOps + Tekton ready</span>
          <h2>Frontend/backend split for the RHUG demo</h2>
          <p>
            Keep the Python backend on the same OpenAI-compatible environment contract while letting the
            user experience evolve independently as a shadcn-style Next.js app.
          </p>
        </div>
        <ChatPanel />
      </div>
    </main>
  );
}
