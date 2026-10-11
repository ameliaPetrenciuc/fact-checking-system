import type { ConfidenceBreakdown as BreakdownType } from "@/lib/types";

interface Props {
  breakdown: BreakdownType;
}

const metrics = [
  { key: "semantic_similarity", label: "Semantic Similarity" },
  { key: "nli_confidence", label: "NLI Confidence" },
  { key: "graph_support", label: "Graph Support" },
  { key: "web_evidence", label: "Web Evidence" },
  { key: "final_confidence", label: "Final Confidence" },
] as const;

export function ConfidenceBreakdown({ breakdown }: Props) {
  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-6">
      <h3 className="font-semibold text-sm text-foreground mb-4">Confidence Breakdown</h3>
      <div className="space-y-3">
        {metrics.map(({ key, label }) => {
          const value = breakdown[key];
          return (
            <div key={key}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">{label}</span>
                <span className="font-medium">{(value * 100).toFixed(0)}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${value * 100}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

