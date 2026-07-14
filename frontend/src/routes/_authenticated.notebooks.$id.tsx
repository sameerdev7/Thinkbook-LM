import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { api, type Session } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pencil, Check, X } from "lucide-react";
import { SourcesPanel } from "@/components/notebook/SourcesPanel";
import { ChatPanel } from "@/components/notebook/ChatPanel";
import { StudioPanel } from "@/components/notebook/StudioPanel";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export const Route = createFileRoute("/_authenticated/notebooks/$id")({
  component: NotebookDetail,
  ssr: false,
});

function NotebookDetail() {
  const { id } = Route.useParams();
  const [session, setSession] = useState<Session | null>(null);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .get<Session>(`/sessions/${id}`)
      .then((s) => setSession(s))
      .catch(() => {});
  }, [id]);

  function startEdit() {
    setName(session?.name || session?.title || "");
    setEditing(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  async function save() {
    const trimmed = name.trim();
    if (!trimmed) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      const updated = await api.patch<Session>(`/sessions/${id}`, {
        name: trimmed,
      });
      setSession((prev) => ({ ...(prev ?? { id }), ...updated }));
      setEditing(false);
    } catch {
      // keep editing open on failure
    } finally {
      setSaving(false);
    }
  }

  const displayName =
    session?.name || session?.title || "Untitled notebook";

  return (
    <div className="flex w-full flex-1 min-h-0">
      {/* Desktop three-pane */}
      <div className="hidden w-full lg:flex">
        <aside className="w-[300px] shrink-0 border-r border-border bg-sidebar">
          <SourcesPanel sessionId={id} />
        </aside>
        <main className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-4">
            {editing ? (
              <>
                <Input
                  ref={inputRef}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") save();
                    if (e.key === "Escape") setEditing(false);
                  }}
                  disabled={saving}
                  className="h-8 max-w-md text-base"
                />
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  onClick={save}
                  disabled={saving}
                  aria-label="Save name"
                >
                  <Check className="h-4 w-4" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  onClick={() => setEditing(false)}
                  aria-label="Cancel"
                >
                  <X className="h-4 w-4" />
                </Button>
              </>
            ) : (
              <>
                <h1
                  className="truncate text-base font-semibold tracking-tight"
                  onDoubleClick={startEdit}
                  title="Double-click to rename"
                >
                  {displayName}
                </h1>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7 text-muted-foreground hover:text-foreground"
                  onClick={startEdit}
                  aria-label="Rename notebook"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </Button>
              </>
            )}
          </div>
          <ChatPanel sessionId={id} />
        </main>
        <aside className="w-[400px] shrink-0 border-l border-border bg-sidebar">
          <StudioPanel sessionId={id} />
        </aside>
      </div>

      {/* Mobile / tablet tabs */}
      <div className="flex w-full flex-col lg:hidden">
        <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-4">
          {editing ? (
            <>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") save();
                  if (e.key === "Escape") setEditing(false);
                }}
                disabled={saving}
                className="h-8 text-base"
              />
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8"
                onClick={save}
                disabled={saving}
                aria-label="Save name"
              >
                <Check className="h-4 w-4" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8"
                onClick={() => setEditing(false)}
                aria-label="Cancel"
              >
                <X className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <h1
                className="flex-1 truncate text-base font-semibold tracking-tight"
                onDoubleClick={startEdit}
              >
                {displayName}
              </h1>
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7 text-muted-foreground"
                onClick={startEdit}
                aria-label="Rename notebook"
              >
                <Pencil className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
        </div>
        <Tabs defaultValue="chat" className="flex flex-1 flex-col">
          <TabsList className="mx-3 mt-3 grid grid-cols-3">
            <TabsTrigger value="sources" className="text-base">Sources</TabsTrigger>
            <TabsTrigger value="chat" className="text-base">Chat</TabsTrigger>
            <TabsTrigger value="studio" className="text-base">Studio</TabsTrigger>
          </TabsList>
          <TabsContent value="sources" className="flex-1 min-h-0 border-t border-border">
            <SourcesPanel sessionId={id} />
          </TabsContent>
          <TabsContent value="chat" className="flex-1 min-h-0 border-t border-border">
            <ChatPanel sessionId={id} />
          </TabsContent>
          <TabsContent value="studio" className="flex-1 min-h-0 border-t border-border">
            <StudioPanel sessionId={id} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}