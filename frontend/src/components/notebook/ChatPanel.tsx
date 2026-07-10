import { useEffect, useRef, useState } from "react";
import { api, type ChatResponse, type ChatSource, type Chunk } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useFeatures } from "@/lib/features-context";
import { Send, Loader2, Sparkles } from "lucide-react";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources?: ChatSource[];
}

function CitationChip({
  sessionId,
  source,
}: {
  sessionId: string;
  source: ChatSource;
}) {
  const [chunk, setChunk] = useState<Chunk | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (chunk || loading) return;
    setLoading(true);
    try {
      const c = await api.get<Chunk>(
        `/sessions/${sessionId}/chunks/${source.chunk_id}`,
      );
      setChunk(c);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  const label = source.reference.replace(/[\[\]]/g, "");

  return (
    <HoverCard openDelay={100} closeDelay={100}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          onMouseEnter={load}
          onFocus={load}
          onClick={load}
          className="mx-0.5 inline-flex h-4 min-w-[1.1rem] items-center justify-center rounded border border-primary/40 bg-primary/10 px-1 text-[10px] font-medium text-primary hover:bg-primary/20"
        >
          {label}
        </button>
      </HoverCardTrigger>
      <HoverCardContent side="top" className="w-80 space-y-2 text-xs">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate font-medium">
            {source.source_file || source.source_type}
          </span>
          {source.page_number != null && (
            <span className="text-muted-foreground">p. {source.page_number}</span>
          )}
        </div>
        <div className="max-h-48 overflow-y-auto rounded-md bg-muted p-2 leading-relaxed text-foreground/90">
          {loading ? "Loading…" : error ? error : (chunk?.content ?? "No preview")}
        </div>
        <div className="text-[10px] text-muted-foreground">
          relevance {(source.relevance_score ?? 0).toFixed(2)}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}

function renderWithCitations(
  text: string,
  sources: ChatSource[] | undefined,
  sessionId: string,
) {
  if (!sources || sources.length === 0) return text;
  const byRef = new Map(sources.map((s) => [s.reference, s]));
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const src = byRef.get(part);
    if (src) return <CitationChip key={i} sessionId={sessionId} source={src} />;
    return <span key={i}>{part}</span>;
  });
}

export function ChatPanel({ sessionId }: { sessionId: string }) {
  const features = useFeatures();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const q = input.trim();
    if (!q || sending || !features.chat) return;
    setInput("");
    setError(null);
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      text: q,
    };
    setMessages((m) => [...m, userMsg]);
    setSending(true);
    try {
      const res = await api.post<ChatResponse>(`/sessions/${sessionId}/chat`, {
        query: q,
      });
      setMessages((m) => [
        ...m,
        {
          id: `a-${Date.now()}`,
          role: "assistant",
          text: res.response,
          sources: res.sources,
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center p-8">
            <div className="max-w-md text-center">
              <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-secondary">
                <Sparkles className="h-5 w-5 text-primary" />
              </div>
              <h3 className="text-base font-medium">Ask across your sources</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Answers come with inline citations. Hover any{" "}
                <span className="mx-0.5 inline-flex h-4 min-w-[1.1rem] items-center justify-center rounded border border-primary/40 bg-primary/10 px-1 text-[10px] font-medium text-primary">
                  1
                </span>{" "}
                to see the source passage.
              </p>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-6 p-6">
            {messages.map((m) => (
              <div key={m.id} className="space-y-1.5">
                <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  {m.role === "user" ? "You" : "Thinkbook"}
                </div>
                <div
                  className={
                    m.role === "user"
                      ? "whitespace-pre-wrap rounded-lg border border-border bg-card p-3 text-sm"
                      : "whitespace-pre-wrap text-sm leading-relaxed text-foreground"
                  }
                >
                  {m.role === "assistant"
                    ? renderWithCitations(m.text, m.sources, sessionId)
                    : m.text}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Thinking…
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="border-t border-border bg-sidebar/50 p-3">
        <div className="mx-auto max-w-3xl">
          {!features.chat && (
            <p className="mb-2 text-xs text-muted-foreground">
              Chat is not configured on the server.
            </p>
          )}
          {error && (
            <p className="mb-2 text-xs text-destructive" role="alert">{error}</p>
          )}
          <div className="flex items-end gap-2 rounded-lg border border-border bg-card p-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder={
                features.chat ? "Ask your sources anything…" : "Chat unavailable"
              }
              disabled={!features.chat}
              rows={1}
              className="min-h-[36px] resize-none border-0 bg-transparent px-1 text-sm shadow-none focus-visible:ring-0"
            />
            <Button
              size="icon"
              onClick={send}
              disabled={!features.chat || sending || !input.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}