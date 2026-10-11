import { useState } from "react";
import { factCheckClaim } from "@/lib/api";
import type { FactCheckResult } from "@/lib/types";
import { ClaimInput } from "@/components/ClaimInput";
import { VerdictCard } from "@/components/VerdictCard";
import { ConfidenceBreakdown } from "@/components/ConfidenceBreakdown";
import { PipelineTimeline } from "@/components/PipelineTimeline";
import { EvidencePanel } from "@/components/EvidencePanel";
import { DeliberationPanel } from "@/components/DeliberationPanel";
import { KGUpdateSummary } from "@/components/KGUpdateSummary";
import { RightReasoningPanel } from "@/components/RightReasoningPanel";

export function FactCheckPage() {
  const [result, setResult] = useState<FactCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (claim: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await factCheckClaim(claim);
      setResult(data);
    } catch (e: any) {
      setError(e.message || "An error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        <div className="lg:col-span-3 space-y-6">
          <ClaimInput onSubmit={handleSubmit} loading={loading} />

          {error && (
            <div className="bg-danger/10 border border-danger/20 text-danger rounded-xl p-4 text-sm">
              {error}
            </div>
          )}

          {result && (
            <>
              <VerdictCard result={result} />
              <ConfidenceBreakdown breakdown={result.confidence_breakdown} />
              <PipelineTimeline steps={result.pipeline_steps} />
              <EvidencePanel evidence={result.evidence} />
              {result.tribunal.used && (
                <DeliberationPanel tribunal={result.tribunal} />
              )}
              <KGUpdateSummary update={result.kg_update} />
            </>
          )}
        </div>

        <div className="lg:col-span-2">
          <div className="sticky top-8">
            <RightReasoningPanel
              result={result}
              loading={loading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

