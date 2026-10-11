import type { Evidence } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ExternalLink, ThumbsUp, ThumbsDown, Minus } from "lucide-react";

interface Props {
  evidence: Evidence[];
}

const typeConfig = {
  supporting: { icon: ThumbsUp, color: "text-success", bg: "bg-success/10" },
  contradicting: { icon: ThumbsDown, color: "text-danger", bg: "bg-danger/10" },
  neutral: { icon: Minus, color: "text-muted-foreground", bg: "bg-muted" },
};

export function EvidencePanel({ evidence }: Props) {
  if (!evidence.length) return null;

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-6">
      <h3 className="font-semibold text-sm text-foreground mb-4">
        Evidence Used ({evidence.length} sources)
      </h3>
      <div className="space-y-3">
        {evidence.map((ev, i) => {
          const config = typeConfig[ev.evidence_type] || typeConfig.neutral;
          const Icon = config.icon;
          return (
            <div key={i} className="border border-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={cn("p-1 rounded", config.bg)}>
                    <Icon className={cn("h-3 w-3", config.color)} />
                  </div>
                  <span className="font-medium text-sm">{ev.source_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {(ev.relevance_score * 100).toFixed(0)}% relevant
                  </span>
                  {ev.url && ev.url !== "N/A" && (
                    <a
                      href={ev.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:text-primary/80 transition"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                {ev.passage}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

