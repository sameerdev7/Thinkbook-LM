import { useEffect, useRef, useState } from "react";
import { api, pollJob, type Job, type Source } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useFeatures } from "@/lib/features-context";
import {
  Upload,
  Youtube,
  Globe,
  AudioLines,
  FileText,
  Plus,
  Loader2,
} from "lucide-react";
import { JobProgress } from "./JobProgress";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

function iconFor(type?: string) {
  const t = (type ?? "").toLowerCase();
  if (t.includes("audio")) return AudioLines;
  if (t.includes("youtube") || t.includes("video")) return Youtube;
  if (t.includes("web") || t.includes("url")) return Globe;
  return FileText;
}

export function SourcesPanel({ sessionId }: { sessionId: string }) {
  const features = useFeatures();
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ytUrl, setYtUrl] = useState("");
  const [webUrl, setWebUrl] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    try {
      const data = await api.get<Source[] | { sources: Source[] }>(
        `/sessions/${sessionId}/sources`,
      );
      const list = Array.isArray(data) ? data : (data.sources ?? []);
      setSources(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sources");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  function trackJob(job: Job) {
    setJobs((prev) => ({ ...prev, [job.id]: job }));
    pollJob(job.id, {
      onUpdate: (j) => setJobs((prev) => ({ ...prev, [j.id]: j })),
    })
      .then((final) => {
        setJobs((prev) => ({ ...prev, [final.id]: final }));
        if (final.status === "completed") refresh();
        setTimeout(() => {
          setJobs((prev) => {
            const next = { ...prev };
            delete next[final.id];
            return next;
          });
        }, 4000);
      })
      .catch(() => {});
  }

  async function uploadDoc(file: File) {
    setUploading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api.postForm<Source>(
        `/sessions/${sessionId}/sources/documents`,
        fd,
      );
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function uploadAudio(file: File) {
    try {
      const fd = new FormData();
      fd.append("file", file);
      const job = await api.postForm<Job>(
        `/sessions/${sessionId}/sources/audio`,
        fd,
      );
      trackJob(job);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Audio upload failed");
    }
  }

  async function addYoutube() {
    if (!ytUrl.trim()) return;
    try {
      const job = await api.post<Job>(`/sessions/${sessionId}/sources/youtube`, {
        url: ytUrl.trim(),
      });
      setYtUrl("");
      trackJob(job);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  async function addWeb() {
    if (!webUrl.trim()) return;
    try {
      const job = await api.post<Job>(`/sessions/${sessionId}/sources/web`, {
        url: webUrl.trim(),
      });
      setWebUrl("");
      trackJob(job);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  const activeJobs = Object.values(jobs);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border p-4">
        <h2 className="text-sm font-semibold tracking-tight">Sources</h2>
        <Popover>
          <PopoverTrigger asChild>
            <Button size="sm" variant="secondary" className="h-7 gap-1 px-2 text-xs">
              <Plus className="h-3.5 w-3.5" /> Add
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-72 space-y-3">
            <div className="space-y-1.5">
              <div className="text-xs font-medium text-muted-foreground">Upload</div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 justify-start gap-2"
                  disabled={!features.document_upload || uploading}
                  onClick={() => fileRef.current?.click()}
                  title={
                    !features.document_upload
                      ? "Document upload not configured"
                      : undefined
                  }
                >
                  {uploading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Upload className="h-3.5 w-3.5" />
                  )}
                  Document
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 justify-start gap-2"
                  disabled={!features.audio_upload}
                  onClick={() => audioRef.current?.click()}
                  title={
                    !features.audio_upload
                      ? "Audio upload not configured"
                      : undefined
                  }
                >
                  <AudioLines className="h-3.5 w-3.5" />
                  Audio
                </Button>
              </div>
              {!features.document_upload && (
                <p className="text-[11px] text-muted-foreground">
                  Document upload is not configured on the server.
                </p>
              )}
              {!features.audio_upload && (
                <p className="text-[11px] text-muted-foreground">
                  Audio upload is not configured on the server.
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <div className="text-xs font-medium text-muted-foreground">YouTube</div>
              <div className="flex gap-2">
                <Input
                  placeholder="https://youtube.com/…"
                  value={ytUrl}
                  onChange={(e) => setYtUrl(e.target.value)}
                  disabled={!features.youtube}
                  className="h-8 text-xs"
                />
                <Button
                  size="sm"
                  onClick={addYoutube}
                  disabled={!features.youtube || !ytUrl.trim()}
                >
                  <Youtube className="h-3.5 w-3.5" />
                </Button>
              </div>
              {!features.youtube && (
                <p className="text-[11px] text-muted-foreground">
                  YouTube ingestion is not configured.
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <div className="text-xs font-medium text-muted-foreground">Web page</div>
              <div className="flex gap-2">
                <Input
                  placeholder="https://…"
                  value={webUrl}
                  onChange={(e) => setWebUrl(e.target.value)}
                  disabled={!features.web_scraping}
                  className="h-8 text-xs"
                />
                <Button
                  size="sm"
                  onClick={addWeb}
                  disabled={!features.web_scraping || !webUrl.trim()}
                >
                  <Globe className="h-3.5 w-3.5" />
                </Button>
              </div>
              {!features.web_scraping && (
                <p className="text-[11px] text-muted-foreground">
                  Web scraping is not configured.
                </p>
              )}
            </div>
          </PopoverContent>
        </Popover>
      </div>

      <input
        ref={fileRef}
        type="file"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) uploadDoc(f);
          e.target.value = "";
        }}
      />
      <input
        ref={audioRef}
        type="file"
        accept="audio/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) uploadAudio(f);
          e.target.value = "";
        }}
      />

      <div className="flex-1 overflow-y-auto p-3">
        {error && (
          <p className="mb-2 text-xs text-destructive" role="alert">{error}</p>
        )}
        {activeJobs.length > 0 && (
          <div className="mb-3 space-y-2">
            {activeJobs.map((j) => (
              <JobProgress key={j.id} job={j} label={j.job_type} />
            ))}
          </div>
        )}
        {loading ? (
          <div className="text-xs text-muted-foreground">Loading…</div>
        ) : sources.length === 0 ? (
          <div className="rounded-md border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
            No sources yet. Add documents, audio, YouTube, or web pages.
          </div>
        ) : (
          <ul className="space-y-1">
            {sources.map((s) => {
              const Icon = iconFor(s.source_type);
              const name =
                s.title || s.name || s.source_file || `Source ${s.id.slice(0, 6)}`;
              return (
                <li
                  key={s.id}
                  className="flex items-start gap-2 rounded-md p-2 text-xs hover:bg-accent"
                >
                  <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-foreground">{name}</div>
                    <div className="truncate text-[11px] text-muted-foreground">
                      {s.source_type}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}