import type { UnifiedFinding, UnifiedFindingSeverity, UnifiedFindingType } from "@/types/api";
import { Badge, InfoTip } from "../../primitives";

/**
 * The export's generic `Finding`/`FindingCard` model only a 3-level
 * severity (high/medium/low) and 3-way source. Our real `/findings`
 * endpoint returns a richer 5-level severity (adds critical/
 * informational) and 4-way type (adds "derived"), plus evidence/
 * explanation/implication/recommended_next_step fields the generic
 * card has no slot for. Rather than lossily collapsing critical into
 * high and dropping the extra fields, this renders the real shape
 * directly, in the same visual language as the export's `FindingCard`.
 */

type BadgeTone = "neutral" | "accent" | "danger" | "warn" | "good";

const severityTone: Record<UnifiedFindingSeverity, BadgeTone> = {
  critical: "danger",
  high: "danger",
  medium: "warn",
  low: "neutral",
  informational: "neutral",
};

const severityLabel: Record<UnifiedFindingSeverity, string> = {
  critical: "CRITICAL",
  high: "HIGH",
  medium: "MEDIUM",
  low: "LOW",
  informational: "INFO",
};

export function UnifiedSeverityBadge({ severity }: { severity: UnifiedFindingSeverity }) {
  return <Badge tone={severityTone[severity]}>{severityLabel[severity]}</Badge>;
}

const typeLabel: Record<UnifiedFindingType, string> = {
  deterministic: "AUTOMATED CHECK",
  document_stated: "FROM THE DOCUMENT",
  ai_inferred: "KORA'S INFERENCE",
  derived: "DERIVED",
};

export function UnifiedTypeBadge({ type }: { type: UnifiedFindingType }) {
  return (
    <span className="inline-flex items-center gap-1">
      <Badge tone="neutral">{typeLabel[type]}</Badge>
      {type === "ai_inferred" && (
        <InfoTip text="Not stated directly — this is Kora's educated guess based on what's in the document." />
      )}
    </span>
  );
}

const severityAccent: Record<UnifiedFindingSeverity, { rail: string; frame: string }> = {
  critical: {
    rail: "bg-danger shadow-glow-danger",
    frame: "border-danger/[0.24] hover:border-danger/[0.42] bg-gradient-to-r from-danger/[0.09] to-white/[0.012]",
  },
  high: {
    rail: "bg-danger shadow-glow-danger",
    frame: "border-danger/[0.16] hover:border-danger/[0.34] bg-gradient-to-r from-danger/[0.06] to-white/[0.012]",
  },
  medium: {
    rail: "bg-warn shadow-glow-warn",
    frame: "border-warn/[0.16] hover:border-warn/[0.34] bg-gradient-to-r from-warn/[0.055] to-white/[0.012]",
  },
  low: {
    rail: "bg-white/30",
    frame: "border-white/[0.08] hover:border-white/20 bg-white/[0.015]",
  },
  informational: {
    rail: "bg-white/20",
    frame: "border-white/[0.06] hover:border-white/15 bg-white/[0.01]",
  },
};

export function UnifiedFindingCard({ finding, compact = false, onClick }: {
  finding: UnifiedFinding;
  compact?: boolean;
  onClick?: () => void;
}) {
  const tone = severityAccent[finding.severity];
  return (
    <article
      onClick={onClick}
      className={
        "relative rounded-xl border transition-colors " +
        tone.frame +
        (compact ? " py-[13px] pl-4 pr-3.5" : " py-[18px] pl-[22px] pr-5") +
        (onClick ? " cursor-pointer" : "")
      }
    >
      <span className={"absolute left-0 w-0.5 rounded " + tone.rail + " " + (compact ? "top-3 bottom-3" : "top-4 bottom-4")} />
      <div className="mb-2 flex flex-wrap items-center gap-[7px]">
        <UnifiedSeverityBadge severity={finding.severity} />
        <UnifiedTypeBadge type={finding.type} />
        <span className="font-mono text-[10px] text-fg-faint">{finding.category.replace(/_/g, " ")}</span>
      </div>
      <h3 className={"mb-1 font-medium " + (compact ? "text-[14.5px]" : "text-[15px]")}>{finding.title}</h3>
      {finding.evidence && (
        <p className="m-0 mb-1 text-[13px] leading-relaxed text-fg-muted [text-wrap:pretty]">{finding.evidence}</p>
      )}
      {finding.explanation && (
        <p className="m-0 mb-1 text-[13px] leading-relaxed text-fg-muted [text-wrap:pretty]">{finding.explanation}</p>
      )}
      {!compact && finding.implication && (
        <p className="m-0 mt-2 text-[12.5px] leading-relaxed text-fg-dim [text-wrap:pretty]">
          <span className="font-medium text-fg-muted">Why it matters: </span>
          {finding.implication}
        </p>
      )}
      {!compact && finding.recommended_next_step && (
        <p className="m-0 mt-2.5 rounded-[9px] bg-accent/[0.08] px-3 py-2 text-[12.5px] leading-relaxed text-fg-tertiary [text-wrap:pretty]">
          <span className="font-medium text-accent-pale">Ask the founder: </span>
          {finding.recommended_next_step}
        </p>
      )}
    </article>
  );
}
