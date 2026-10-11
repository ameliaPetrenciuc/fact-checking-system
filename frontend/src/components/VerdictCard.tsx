import type { FactCheckResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, HelpCircle, Clock, Database, Globe } from "lucide-react";

interface Props {
  result: FactCheckResult;
}

const verdictConfig = {
  TRUE: { color: "bg-success/10 border-success/30 text-success", icon: CheckCircle2, label: "TRUE" },
  FALSE: { color: "bg-danger/10 border-danger/30 text-danger", icon: XCircle, label: "FALSE" },
  NEUTRAL: { color: "bg-warning/10 border-warning/30 text-warning", icon: HelpCircle, label: "NEUTRAL" },
};

export function VerdictCard({ result }: Props) {
  const config = verdictConfig[result.verdict] || verdictConfig.NEUTRAL;
  const Icon = config.icon;

  return (
    <div className={cn("rounded-xl border-2 p-6 shadow-sm", config.color)}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Icon className="h-8 w-8" />
          <div>
            <h3 className="text-2xl font-bold">{config.label}</h3>
            <p className="text-sm opacity-80">Verdict</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold">{(result.confidence * 100).toFixed(0)}%</p>
          <p className="text-sm opacity-80">Confidence</p>
        </div>
      </div>

      <p className="text-sm leading-relaxed opacity-90 mb-4">{result.explanation}</p>

      <div className="flex items-center gap-4 text-xs opacity-70">
        <span className="flex items-center gap-1">
          {result.decision_source.includes("Knowledge Graph") ? (
            <Database className="h-3 w-3" />
          ) : (
            <Globe className="h-3 w-3" />
          )}
          {result.decision_source}
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {result.elapsed_seconds}s
        </span>
      </div>
    </div>
  );
}

