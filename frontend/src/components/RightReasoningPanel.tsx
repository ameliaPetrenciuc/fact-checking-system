import type { FactCheckResult } from "@/lib/types";
import { KGGraphPreview } from "./KGGraphPreview";
import { Network, AlertTriangle, GitBranch, Search, CheckCircle2 } from "lucide-react";

interface Props {
  result: FactCheckResult | null;
  loading: boolean;
}

export function RightReasoningPanel({ result, loading }: Props) {
  // State 1: Loading
  if (loading) {
    return (
      <div className="bg-card rounded-xl border border-border shadow-sm p-8 flex flex-col items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4 w-full max-w-xs">
          <Search className="h-10 w-10 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground text-center">
            Analyzing claim through the pipeline...
          </p>
          <div className="w-full h-1 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-primary/60 rounded-full animate-pulse" style={{ width: "60%" }} />
          </div>
        </div>
      </div>
    );
  }

  // State 1: Before verification
  if (!result) {
    return (
      <div className="bg-card rounded-xl border border-border shadow-sm p-8 flex flex-col items-center justify-center min-h-[400px]">
        <Network className="h-12 w-12 text-muted-foreground/30 mb-4" />
        <p className="text-sm text-muted-foreground text-center">
          Submit a claim to explore the reasoning path.
        </p>
      </div>
    );
  }

  const { graph_preview } = result;

  // State 2: KG answered — show graph
  if (graph_preview.status === "kg_answered" && graph_preview.nodes.length > 0) {
    return (
      <div className="space-y-4">
        <div className="bg-card rounded-xl border border-border shadow-sm p-4">
          <div className="flex items-center gap-2 mb-2">
            <Network className="h-4 w-4 text-primary" />
            <h3 className="font-semibold text-sm">Knowledge Graph Match</h3>
          </div>
          <p className="text-xs text-muted-foreground">{graph_preview.message}</p>
        </div>
        <KGGraphPreview nodes={graph_preview.nodes} edges={graph_preview.edges} />
      </div>
    );
  }

  // State 3: No KG match — show fallback explanation
  if (graph_preview.status === "no_kg_match") {
    return (
      <div className="space-y-4">
        <div className="bg-card rounded-xl border border-border shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="h-5 w-5 text-warning" />
            <h3 className="font-semibold text-sm">Web Fallback Triggered</h3>
          </div>
          <div className="bg-warning/5 border border-warning/20 rounded-lg p-4">
            <pre className="text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed font-sans">
              {graph_preview.message}
            </pre>
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            The system does not force an answer from the Knowledge Graph when confidence is too low.
            Web verification ensures reliable results.
          </p>
        </div>
        {result.kg_result.used && result.kg_result.matched_claim && (
          <div className="bg-card rounded-xl border border-border shadow-sm p-4">
            <p className="text-xs text-muted-foreground mb-1">Closest KG Match (insufficient):</p>
            <p className="text-sm text-foreground italic">"{result.kg_result.matched_claim}"</p>
            <p className="text-xs text-muted-foreground mt-1">
              Score: {(result.kg_result.similarity_score * 100).toFixed(0)}% | Strategy: {result.kg_result.strategy}
            </p>
          </div>
        )}
      </div>
    );
  }

  // State 4: New knowledge preview
  if (graph_preview.status === "new_knowledge_preview" && graph_preview.nodes.length > 0) {
    return (
      <div className="space-y-4">
        <div className="bg-card rounded-xl border border-border shadow-sm p-4">
          <div className="flex items-center gap-2 mb-2">
            <GitBranch className="h-4 w-4 text-primary" />
            <h3 className="font-semibold text-sm">New Knowledge Extracted</h3>
          </div>
          <p className="text-xs text-muted-foreground">{graph_preview.message}</p>
        </div>
        <KGGraphPreview nodes={graph_preview.nodes} edges={graph_preview.edges} />
        {result.kg_update.source_url && (
          <div className="bg-card rounded-xl border border-border shadow-sm p-4">
            <p className="text-xs text-muted-foreground">
              Primary source:{" "}
              <a href={result.kg_update.source_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                {result.kg_update.source_url.split("//")[1]?.split("/")[0]}
              </a>
            </p>
            <p className="text-xs text-success mt-1 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Stored in Knowledge Graph
            </p>
          </div>
        )}
      </div>
    );
  }

  // Default fallback
  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-8 flex flex-col items-center justify-center min-h-[400px]">
      <Network className="h-12 w-12 text-muted-foreground/30 mb-4" />
      <p className="text-sm text-muted-foreground text-center">
        No graph data available for this result.
      </p>
    </div>
  );
}

