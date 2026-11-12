import { useEffect, useState } from "react";

type Health = { status: string; database: string };

// Stage 1 only proves the frontend can reach the backend. The real UI starts in Stage 3.
export default function App() {
  const [health, setHealth] = useState<Health | "error" | null>(null);

  useEffect(() => {
    fetch("/api/v1/health")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setHealth)
      .catch(() => setHealth("error"));
  }, []);

  return (
    <main className="min-h-screen grid place-items-center bg-neutral-950 text-neutral-100">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-semibold">Tunewise</h1>
        <p className="text-neutral-400">Understand your music. Discover beyond it.</p>
        <p className="text-sm text-neutral-500">
          API:{" "}
          {health === null ? "checking…" : health === "error" ? "unreachable" : `${health.status} (db ${health.database})`}
        </p>
      </div>
    </main>
  );
}
