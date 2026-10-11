import { useEffect, useState } from "react";
import { getMetrics } from "@/lib/api";
import type { Metrics } from "@/lib/types";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { Database, Globe, TrendingUp, Target, Zap, Award } from "lucide-react";

const ACADEMIC_PALETTE = {
  primary:   "#1e3a5f",
  secondary: "#5b8a72",
  tertiary:  "#a64545",
  quaternary:"#c9a227",
  neutral:   "#64748b",
  accent:    "#7d6b91",
  grid:      "#cbd5e1",
  axis:      "#475569",
};

const VERDICT_COLORS: Record<string, string> = {
  TRUE:    "#4f7d5e",
  FALSE:   "#a64545",
  NEUTRAL: "#9ca3af",
};

const PIE_FALLBACK = [
  ACADEMIC_PALETTE.primary,
  ACADEMIC_PALETTE.tertiary,
  ACADEMIC_PALETTE.quaternary,
  ACADEMIC_PALETTE.secondary,
];

const tooltipStyle = {
  backgroundColor: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: "8px",
  fontSize: "12px",
  boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)",
  padding: "8px 12px",
};

export function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    getMetrics().then(setMetrics).catch(console.error);
  }, []);

  if (!metrics) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-12 text-center text-muted-foreground">
        Loading metrics...
      </div>
    );
  }

  const verdictData = Object.entries(metrics.verdict_distribution).map(([k, v]) => ({
    name: k, value: v,
  }));

  const sourceData = Object.entries(metrics.source_type_breakdown).map(([k, v]) => ({
    name: k, value: v,
  }));

  const baselineData = Object.entries(metrics.baseline_comparison).map(([system, vals]) => ({
    name: system === "system" ? "Our System" : system === "llama_70b" ? "Llama 70B" : "Llama 8B",
    Accuracy: (vals.accuracy * 100),
    F1: (vals.f1 * 100),
    Precision: (vals.precision * 100),
    Recall: (vals.recall * 100),
  }));

  const kpiCards = [
    { label: "Total Claims",    value: metrics.total_claims,                                  icon: Database },
    { label: "Accuracy",        value: `${(metrics.accuracy * 100).toFixed(1)}%`,             icon: Target   },
    { label: "F1 Score",        value: `${(metrics.f1_score * 100).toFixed(1)}%`,             icon: Award    },
    { label: "KG Hit Rate",     value: `${(metrics.kg_hit_rate * 100).toFixed(0)}%`,          icon: Zap      },
    { label: "Web Fallback",    value: `${(metrics.web_fallback_rate * 100).toFixed(0)}%`,    icon: Globe    },
    { label: "Avg Confidence",  value: `${(metrics.average_confidence * 100).toFixed(0)}%`,   icon: TrendingUp },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">Evaluation Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          System performance metrics on the Check-COVID dataset (333 claims)
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {kpiCards.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.label} className="bg-card rounded-xl border border-border shadow-sm p-4">
              <Icon className="h-5 w-5 mb-2" style={{ color: ACADEMIC_PALETTE.primary }} />
              <p className="text-2xl font-bold text-foreground">{kpi.value}</p>
              <p className="text-xs text-muted-foreground">{kpi.label}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-card rounded-xl border border-border shadow-sm p-6">
          <h3 className="font-semibold text-sm mb-1 text-foreground">Verdict Distribution</h3>
          <p className="text-xs text-muted-foreground mb-4">
            Share of verdicts emitted on the evaluation set
          </p>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={verdictData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={88}
                innerRadius={42}
                paddingAngle={2}
                stroke="#ffffff"
                strokeWidth={2}
                label={{ fontSize: 11, fill: ACADEMIC_PALETTE.axis }}
              >
                {verdictData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={VERDICT_COLORS[entry.name] || PIE_FALLBACK[i % PIE_FALLBACK.length]}
                  />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
              <Legend
                iconType="circle"
                wrapperStyle={{ fontSize: 12, color: ACADEMIC_PALETTE.axis }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-card rounded-xl border border-border shadow-sm p-6">
          <h3 className="font-semibold text-sm mb-1 text-foreground">Decision Source Breakdown</h3>
          <p className="text-xs text-muted-foreground mb-4">
            Resolution rate from Knowledge Graph vs. web investigation
          </p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={sourceData} margin={{ top: 10, right: 16, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={ACADEMIC_PALETTE.grid} vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: ACADEMIC_PALETTE.axis }}
                axisLine={{ stroke: ACADEMIC_PALETTE.grid }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: ACADEMIC_PALETTE.axis }}
                axisLine={{ stroke: ACADEMIC_PALETTE.grid }}
                tickLine={false}
              />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(30,58,95,0.06)" }} />
              <Bar
                dataKey="value"
                fill={ACADEMIC_PALETTE.primary}
                radius={[3, 3, 0, 0]}
                maxBarSize={64}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border shadow-sm p-6">
        <h3 className="font-semibold text-sm mb-1 text-foreground">System vs. LLM Baselines</h3>
        <p className="text-xs text-muted-foreground mb-4">
          Comparison on standard metrics (values in %)
        </p>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={baselineData} margin={{ top: 10, right: 24, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={ACADEMIC_PALETTE.grid} vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 12, fill: ACADEMIC_PALETTE.axis }}
              axisLine={{ stroke: ACADEMIC_PALETTE.grid }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: ACADEMIC_PALETTE.axis }}
              axisLine={{ stroke: ACADEMIC_PALETTE.grid }}
              tickLine={false}
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              cursor={{ fill: "rgba(30,58,95,0.06)" }}
              formatter={(v) => `${Number(v).toFixed(1)}%`}
            />
            <Legend
              iconType="square"
              wrapperStyle={{ fontSize: 12, color: ACADEMIC_PALETTE.axis, paddingTop: 8 }}
            />
            <Bar dataKey="Accuracy"  fill={ACADEMIC_PALETTE.primary}    radius={[3, 3, 0, 0]} maxBarSize={42} />
            <Bar dataKey="F1"        fill={ACADEMIC_PALETTE.secondary}  radius={[3, 3, 0, 0]} maxBarSize={42} />
            <Bar dataKey="Precision" fill={ACADEMIC_PALETTE.quaternary} radius={[3, 3, 0, 0]} maxBarSize={42} />
            <Bar dataKey="Recall"    fill={ACADEMIC_PALETTE.tertiary}   radius={[3, 3, 0, 0]} maxBarSize={42} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
