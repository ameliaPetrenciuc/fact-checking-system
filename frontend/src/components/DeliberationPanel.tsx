import { useState } from "react";
import type { Tribunal } from "@/lib/types";
import {
  ShieldCheck,
  ShieldAlert,
  Gavel,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface Props {
  tribunal: Tribunal;
}

interface ReasoningCardProps {
  key?: string | number;
  title: string;
  icon:React.ComponentType<{ className?: string }>;
  color: string;
  summary?: string | null;
}

function ReasoningCard({
  title,
  icon: Icon,
  color,
  summary,
}: ReasoningCardProps) {
  const [expanded, setExpanded] = useState(false);

  const text = summary?.trim() || "No summary available.";

  return (
    <div className="border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${color}`} />
        <span className="font-medium text-sm">{title}</span>
      </div>

      <p
        className={`text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap ${
          expanded ? "" : "line-clamp-4"
        }`}
      >
        {text}
      </p>

      {text.length > 250 && (
        <button
          type="button"
          onClick={() => setExpanded((previous) => !previous)}
          className="mt-2 flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
          {expanded ? (
            <>
              Show less
              <ChevronUp className="h-3 w-3" />
            </>
          ) : (
            <>
              Show more
              <ChevronDown className="h-3 w-3" />
            </>
          )}
        </button>
      )}
    </div>
  );
}

export function DeliberationPanel({ tribunal }: Props) {
  if (!tribunal.used) return null;

  const cards = [
    {
      title: "Claim Advocate",
      icon: ShieldCheck,
      color: "text-success",
      summary: tribunal.advocate_summary,
    },
    {
      title: "Claim Challenger",
      icon: ShieldAlert,
      color: "text-danger",
      summary: tribunal.challenger_summary,
    },
    {
      title: "Verdict Judge",
      icon: Gavel,
      color: "text-primary",
      summary: tribunal.judge_summary,
    },
  ];

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-6">
      <h3 className="font-semibold text-sm text-foreground mb-4">
        Agentic Tribunal Reasoning
      </h3>

      <div className="space-y-3">
        {cards.map((card) => (
          <ReasoningCard
            key={card.title}
            title={card.title}
            icon={card.icon}
            color={card.color}
            summary={card.summary}
          />
        ))}
      </div>
    </div>
  );
}