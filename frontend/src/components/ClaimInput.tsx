import { useState } from "react";
import { Search, Loader2 } from "lucide-react";

interface Props {
  onSubmit: (claim: string) => void;
  loading: boolean;
}

export function ClaimInput({ onSubmit, loading }: Props) {
  const [claim, setClaim] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (claim.trim()) onSubmit(claim.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="bg-card rounded-xl border border-border shadow-sm p-6">
      <h2 className="text-lg font-semibold mb-3 text-foreground">Verify a Claim</h2>
      <textarea
        value={claim}
        onChange={(e) => setClaim(e.target.value)}
        placeholder="Enter a factual claim to verify..."
        className="w-full h-28 p-4 border border-border rounded-lg bg-background text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !claim.trim()}
        className="mt-3 w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground font-medium py-3 px-6 rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Verifying...
          </>
        ) : (
          <>
            <Search className="h-4 w-4" />
            Verify Claim
          </>
        )}
      </button>
    </form>
  );
}

