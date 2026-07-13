import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { api, type Session } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Plus, FileText } from "lucide-react";

export const Route = createFileRoute("/_authenticated/notebooks/")({
  component: NotebooksPage,
  ssr: false,
});

function NotebooksPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Session[] | { sessions: Session[] }>("/sessions")
      .then((data) => {
        const list = Array.isArray(data) ? data : (data.sessions ?? []);
        setSessions(list);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  async function createNotebook() {
    setCreating(true);
    try {
      const s = await api.post<Session>("/sessions", {});
      navigate({ to: "/notebooks/$id", params: { id: s.id } });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-5xl p-6 sm:p-10">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Your notebooks</h1>
          <p className="mt-1 text-base text-muted-foreground">
            Collect sources, chat with them, and generate briefings.
          </p>
        </div>
        <Button onClick={createNotebook} disabled={creating}>
          <Plus className="mr-2 h-4 w-4" />
          {creating ? "Creating…" : "New notebook"}
        </Button>
      </div>

      {error && (
        <p className="mb-4 text-base text-destructive" role="alert">{error}</p>
      )}

      {sessions === null ? (
        <div className="text-base text-muted-foreground">Loading…</div>
      ) : sessions.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <FileText className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
          <p className="text-base text-muted-foreground">
            No notebooks yet. Create your first one to get started.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sessions.map((s) => (
            <Link
              key={s.id}
              to="/notebooks/$id"
              params={{ id: s.id }}
              className="group rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent"
            >
              <div className="flex items-start gap-3">
                <div className="rounded-md bg-secondary p-2">
                  <FileText className="h-4 w-4 text-primary" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-base font-medium">
                    {s.title || s.name || "Untitled notebook"}
                  </div>
                  <div className="mt-1 truncate text-sm text-muted-foreground">
                    {s.updated_at
                      ? new Date(s.updated_at).toLocaleString()
                      : s.id.slice(0, 8)}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}