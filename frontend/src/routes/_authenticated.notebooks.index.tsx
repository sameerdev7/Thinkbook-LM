import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { api, type Session } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, FileText, Pencil, Trash2, Check, X } from "lucide-react";

export const Route = createFileRoute("/_authenticated/notebooks/")({
  component: NotebooksPage,
  ssr: false,
});

function NotebooksPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const editInputRef = useRef<HTMLInputElement>(null);

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

  function startEdit(s: Session) {
    setEditingId(s.id);
    setEditValue(s.name || s.title || "");
    setTimeout(() => editInputRef.current?.focus(), 0);
  }

  async function saveEdit(id: string) {
    const name = editValue.trim();
    if (!name) {
      setEditingId(null);
      return;
    }
    setBusyId(id);
    try {
      const updated = await api.patch<Session>(`/sessions/${id}`, { name });
      setSessions((prev) =>
        prev ? prev.map((s) => (s.id === id ? { ...s, ...updated } : s)) : prev,
      );
      setEditingId(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rename failed");
    } finally {
      setBusyId(null);
    }
  }

  async function deleteNotebook(id: string) {
    if (!confirm("Delete this notebook? This cannot be undone.")) return;
    setBusyId(id);
    try {
      await api.del(`/sessions/${id}`);
      setSessions((prev) => (prev ? prev.filter((s) => s.id !== id) : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusyId(null);
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
          {sessions.map((s) => {
            const displayName = s.name || s.title || "Untitled notebook";
            const isEditing = editingId === s.id;
            return (
              <div
                key={s.id}
                className="group relative rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40"
              >
                <div className="flex items-start gap-3">
                  <div className="rounded-md bg-secondary p-2">
                    <FileText className="h-4 w-4 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    {isEditing ? (
                      <div className="flex items-center gap-1">
                        <Input
                          ref={editInputRef}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") saveEdit(s.id);
                            if (e.key === "Escape") setEditingId(null);
                          }}
                          className="h-8 text-base"
                          disabled={busyId === s.id}
                        />
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 shrink-0"
                          onClick={() => saveEdit(s.id)}
                          disabled={busyId === s.id}
                          aria-label="Save name"
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 shrink-0"
                          onClick={() => setEditingId(null)}
                          aria-label="Cancel rename"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      <Link
                        to="/notebooks/$id"
                        params={{ id: s.id }}
                        className="block"
                        onDoubleClick={(e) => {
                          e.preventDefault();
                          startEdit(s);
                        }}
                      >
                        <div
                          className="truncate text-base font-medium hover:text-primary"
                          title="Double-click to rename"
                        >
                          {displayName}
                        </div>
                        <div className="mt-1 truncate text-sm text-muted-foreground">
                          {s.updated_at
                            ? new Date(s.updated_at).toLocaleString()
                            : s.id.slice(0, 8)}
                        </div>
                      </Link>
                    )}
                  </div>
                  {!isEditing && (
                    <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          startEdit(s);
                        }}
                        aria-label="Rename notebook"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          deleteNotebook(s.id);
                        }}
                        disabled={busyId === s.id}
                        aria-label="Delete notebook"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}