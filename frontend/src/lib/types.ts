export interface PipelineStep {
  name: string;
  status: "completed" | "skipped" | "active" | "failed";
  details: string;
}

export interface ConfidenceBreakdown {
  semantic_similarity: number;
  nli_confidence: number;
  graph_support: number;
  web_evidence: number;
  final_confidence: number;
}

export interface KGResult {
  used: boolean;
  matched_claim: string | null;
  similarity_score: number;
  strategy: string | null;
  nli_label: string | null;
  nli_score: number;
  effective_truth: string | null;
  fallback_reason: string | null;
}

export interface WebResult {
  used: boolean;
  query: string | null;
  primary_url: string | null;
  evidence: Array<{ content: string; score: number; source_url: string }>;
  support_summary: string | null;
  contradiction_summary: string | null;
  corrected_claim: string | null;
  deliberation_used: boolean;
}

export interface Evidence {
  source_name: string;
  url: string;
  relevance_score: number;
  evidence_type: "supporting" | "contradicting" | "neutral";
  passage: string;
}

export interface Tribunal {
  used: boolean;
  advocate_summary: string | null;
  challenger_summary: string | null;
  judge_summary: string | null;
}

export interface KGUpdate {
  stored: boolean;
  triples_saved: number;
  corrected_claim: string | null;
  triples: Array<{ subject: string; predicate: string; object: string }>;
  source_url: string | null;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface GraphPreview {
  status: "kg_answered" | "no_kg_match" | "new_knowledge_preview" | "empty";
  message: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface FactCheckResult {
  claim: string;
  verdict: "TRUE" | "FALSE" | "NEUTRAL";
  confidence: number;
  decision_source: string;
  explanation: string;
  pipeline_steps: PipelineStep[];
  confidence_breakdown: ConfidenceBreakdown;
  kg_result: KGResult;
  web_result: WebResult;
  evidence: Evidence[];
  tribunal: Tribunal;
  kg_update: KGUpdate;
  graph_preview: GraphPreview;
  elapsed_seconds: number;
}

export interface Metrics {
  total_claims: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  kg_hit_rate: number;
  web_fallback_rate: number;
  average_confidence: number;
  verdict_distribution: Record<string, number>;
  source_type_breakdown: Record<string, number>;
  baseline_comparison: Record<string, Record<string, number>>;
  pipeline_stats: Record<string, number>;
}

