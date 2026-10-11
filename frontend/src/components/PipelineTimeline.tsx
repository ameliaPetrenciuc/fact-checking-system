import type { PipelineStep } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, SkipForward, Loader2 } from "lucide-react";

interface Props {
  steps: PipelineStep[];
}

const statusIcon = {
  completed: <CheckCircle2 className="h-4 w-4 text-success" />,
  failed: <XCircle className="h-4 w-4 text-danger" />,
  skipped: <SkipForward className="h-4 w-4 text-muted-foreground" />,
  active: <Loader2 className="h-4 w-4 text-primary animate-spin" />,
};

export function PipelineTimeline({ steps }: Props) {
  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-6">
      <h3 className="font-semibold text-sm text-foreground mb-4">Pipeline Timeline</h3>
      <div className="space-y-1">
        {steps.map((step, i) => (
          <div key={i} className="flex items-start gap-3 py-2">
            <div className="mt-0.5 flex-shrink-0">
              {statusIcon[step.status]}
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn(
                "text-sm font-medium",
                step.status === "skipped" ? "text-muted-foreground" : "text-foreground"
              )}>
                {step.name}
              </p>
              <p className="text-xs text-muted-foreground truncate">{step.details}</p>
            </div>
            <span className={cn(
              "text-xs px-2 py-0.5 rounded-full flex-shrink-0",
              step.status === "completed" && "bg-success/10 text-success",
              step.status === "failed" && "bg-danger/10 text-danger",
              step.status === "skipped" && "bg-muted text-muted-foreground",
              step.status === "active" && "bg-primary/10 text-primary"
            )}>
              {step.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

