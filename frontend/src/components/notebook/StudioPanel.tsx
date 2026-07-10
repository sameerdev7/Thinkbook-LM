import { useState } from "react";
import {
  api,
  pollJob,
  podcastAudioDownloadUrl,
  type Job,
  type PodcastAudioResult,
  type PodcastLine,
  type PodcastScriptResult,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useFeatures } from "@/lib/features-context";
import { JobProgress } from "./JobProgress";
import { Mic, AudioLines, Download, Loader2 } from "lucide-react";

function scriptToText(script: PodcastLine[]): string {
  return script
    .map((line) => {
      const [speaker, text] = Object.entries(line)[0] ?? ["", ""];
      return `${speaker}: ${text}`;
    })
    .join("\n\n");
}

function textToScript(text: string): PodcastLine[] {
  const lines: PodcastLine[] = [];
  for (const raw of text.split(/\n+/)) {
    const trimmed = raw.trim();
    if (!trimmed) continue;
    const m = trimmed.match(/^([^:]+):\s*(.*)$/);
    if (m) {
      lines.push({ [m[1].trim()]: m[2].trim() });
    } else {
      lines.push({ "Speaker 1": trimmed });
    }
  }
  return lines;
}

export function StudioPanel({ sessionId }: { sessionId: string }) {
  const features = useFeatures();
  const [scriptJob, setScriptJob] = useState<Job<PodcastScriptResult> | null>(
    null,
  );
  const [audioJob, setAudioJob] = useState<Job<PodcastAudioResult> | null>(null);
  const [scriptText, setScriptText] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioJobId, setAudioJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [rendering, setRendering] = useState(false);

  async function generateScript() {
    setError(null);
    setGenerating(true);
    try {
      const job = await api.post<Job<PodcastScriptResult>>(
        `/sessions/${sessionId}/podcast/script`,
        {},
      );
      setScriptJob(job);
      const final = await pollJob<PodcastScriptResult>(job.id, {
        onUpdate: (j) => setScriptJob(j),
      });
      setScriptJob(final);
      if (final.status === "completed" && final.result?.script) {
        setScriptText(scriptToText(final.result.script));
      } else if (final.status === "failed") {
        setError(final.error ?? "Script generation failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setGenerating(false);
    }
  }

  async function renderAudio() {
    if (!scriptText.trim()) return;
    setError(null);
    setRendering(true);
    setAudioUrl(null);
    setAudioJobId(null);
    try {
      const script = textToScript(scriptText);
      const job = await api.post<Job<PodcastAudioResult>>(
        `/sessions/${sessionId}/podcast/audio`,
        { script },
      );
      setAudioJob(job);
      const final = await pollJob<PodcastAudioResult>(job.id, {
        onUpdate: (j) => setAudioJob(j),
      });
      setAudioJob(final);
      if (final.status === "completed") {
        setAudioJobId(final.id);
        setAudioUrl(podcastAudioDownloadUrl(final.id));
      } else if (final.status === "failed") {
        setError(final.error ?? "Audio generation failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setRendering(false);
    }
  }

  const scriptDisabled = !features.podcast_script;
  const audioDisabled = !features.podcast_audio;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-4">
        <h2 className="text-sm font-semibold tracking-tight">Studio</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Generate an audio briefing from your sources.
        </p>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-medium">
              <Mic className="h-3.5 w-3.5 text-primary" /> Script
            </div>
            <Button
              size="sm"
              variant="secondary"
              className="h-7 text-xs"
              disabled={scriptDisabled || generating}
              onClick={generateScript}
              title={scriptDisabled ? "Podcast script not configured" : undefined}
            >
              {generating ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : null}
              Generate
            </Button>
          </div>
          {scriptDisabled && (
            <p className="text-[11px] text-muted-foreground">
              Podcast script generation is not configured on the server.
            </p>
          )}
          {scriptJob && scriptJob.status !== "completed" && (
            <JobProgress job={scriptJob} label="Generating script" />
          )}
          <Textarea
            value={scriptText}
            onChange={(e) => setScriptText(e.target.value)}
            placeholder='Speaker 1: Welcome…\nSpeaker 2: Today we discuss…'
            className="min-h-[180px] resize-y font-mono text-xs"
          />
        </section>

        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-medium">
              <AudioLines className="h-3.5 w-3.5 text-primary" /> Audio
            </div>
            <Button
              size="sm"
              className="h-7 text-xs"
              disabled={audioDisabled || rendering || !scriptText.trim()}
              onClick={renderAudio}
              title={audioDisabled ? "Podcast audio not configured" : undefined}
            >
              {rendering ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : null}
              Render
            </Button>
          </div>
          {audioDisabled && (
            <p className="text-[11px] text-muted-foreground">
              Podcast audio rendering is not configured on the server.
            </p>
          )}
          {audioJob && audioJob.status !== "completed" && (
            <JobProgress job={audioJob} label="Rendering audio" />
          )}
          {audioUrl && (
            <div className="space-y-2 rounded-md border border-border bg-card p-3">
              <audio controls src={audioUrl} className="w-full" />
              {audioJobId && (
                <a
                  href={audioUrl}
                  download
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  <Download className="h-3 w-3" /> Download
                </a>
              )}
            </div>
          )}
        </section>

        {error && (
          <p className="text-xs text-destructive" role="alert">{error}</p>
        )}
      </div>
    </div>
  );
}