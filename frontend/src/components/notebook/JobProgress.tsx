import { Progress } from "@/components/ui/progress";
import type { Job } from "@/lib/api";

export function JobProgress({ job, label }: { job: Job | null; label?: string }) {
  if (!job) return null;
  const pct = Math.max(0, Math.min(100, Math.round((job.progress ?? 0) * 100)));
  const isDone = job.status === "completed";
  const isFailed = job.status === "failed";
  return (
    <div className="space-y-1.5 rounded-md border border-border bg-card p-3">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-foreground">{label ?? job.job_type}</span>
        <span
          className={
            isFailed
              ? "text-destructive"
              : isDone
                ? "text-primary"
                : "text-muted-foreground"
          }
        >
          {isFailed ? "failed" : isDone ? "done" : job.status}
        </span>
      </div>
      <Progress value={pct} className="h-1.5" />
      <p className="truncate text-xs text-muted-foreground">
        {job.error ?? job.step_message ?? "\u00A0"}
      </p>
    </div>
  );
}