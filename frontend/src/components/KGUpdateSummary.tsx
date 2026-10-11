import type { KGUpdate } from "@/lib/types";
import { Database, ArrowRight } from "lucide-react";

interface Props {
  update: KGUpdate;
}

export function KGUpdateSummary({ update }: Props) {
  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-6">
      <h3 className="font-semibold text-sm text-foreground mb-4">Knowledge Graph Update</h3>

      {update.stored ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-success">
            <Database className="h-4 w-4" />
            <span>{update.triples_saved} triple(s) stored in Neo4j</span>
          </div>

          {update.corrected_claim && (
            <div className="bg-danger/5 border border-danger/20 rounded-lg p-3">
              <p className="text-xs text-muted-foreground mb-1">Corrected Claim:</p>
              <p className="text-sm font-medium text-foreground">{update.corrected_claim}</p>
            </div>
          )}

          {update.triples.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Extracted Triples:</p>
              {update.triples.map((t, i) => (
                <div key={i} className="flex items-center gap-2 text-xs bg-muted/50 rounded-lg p-2">
                  <span className="font-medium text-primary">{t.subject}</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <span className="text-muted-foreground">{t.predicate}</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <span className="font-medium text-primary">{t.object}</span>
                </div>
              ))}
            </div>
          )}

          {update.source_url && (
            <p className="text-xs text-muted-foreground">
              Source: <a href={update.source_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{update.source_url}</a>
            </p>
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No new knowledge was stored for this claim.</p>
      )}
    </div>
  );
}

