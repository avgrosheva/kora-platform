import type { ChecklistItemResult, CoverageAssessmentRead, MissingInformationResponse } from "@/types/api";
import { GapChip, Meter, Panel, SectionLabel, humanizeFieldName } from "../../primitives";

const CATEGORY_LABELS: Record<string, string> = {
  company: "Company Overview", financial: "Financial", market: "Market", team: "Team",
};

function toneFor(pct: number) {
  if (pct >= 100) return "good" as const;
  if (pct >= 60) return "accent" as const;
  if (pct > 0) return "warn" as const;
  return "danger" as const;
}

function textToneFor(pct: number) {
  if (pct >= 100) return "text-good";
  if (pct >= 60) return "text-accent-pale";
  if (pct > 0) return "text-warn";
  return "text-danger-soft";
}

// Groups non-FOUND checklist items by category, preserving first-seen
// order, so each gap shows its recommended_request guidance next to it
// instead of a bare field name.
function groupMissingByCategory(items: ChecklistItemResult[]): [string, ChecklistItemResult[]][] {
  const byCategory = new Map<string, ChecklistItemResult[]>();
  for (const item of items) {
    if (item.status === "found") continue;
    const existing = byCategory.get(item.category);
    if (existing) existing.push(item);
    else byCategory.set(item.category, [item]);
  }
  return Array.from(byCategory.entries());
}

export function CoverageTab({ coverage, missingInfo }: {
  coverage: CoverageAssessmentRead;
  missingInfo: MissingInformationResponse | null;
}) {
  const percent = Math.round(coverage.overall_confidence * 100);
  const categories = Object.entries(coverage.coverage).map(([key, cat]) => ({
    name: CATEGORY_LABELS[key] ?? key,
    filled: cat.found,
    total: cat.required,
    pct: Math.round(cat.score * 100),
  }));
  const grouped = missingInfo ? groupMissingByCategory(missingInfo.items) : [];

  return (
    <div>
      <Panel className="mb-4 px-[26px] py-6">
        <div className="mb-[26px] flex flex-wrap items-start justify-between gap-8">
          <div className="max-w-[640px]">
            <h2 className="mb-2 text-[16px] font-semibold">Analysis coverage</h2>
            <p className="m-0 text-[13.5px] leading-relaxed text-fg-dim [text-wrap:pretty]">
              How complete the information is — and what to ask for next. This reflects how much of a thorough
              due-diligence checklist this document's data covers, not an investment-quality score. A strong
              company with a thin document will still show low coverage here.
            </p>
          </div>
          <div className="text-right">
            <div className={"font-mono text-[38px] tracking-[-1.5px] " + textToneFor(percent)}>{percent}%</div>
            {missingInfo && (
              <div className="font-mono text-[10.5px] tracking-label text-fg-faint">
                {missingInfo.total_found} / {missingInfo.total_required} FIELDS
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-[18px]">
          {categories.map((cat, i) => (
            <div key={cat.name}>
              <div className="mb-2 flex items-baseline justify-between">
                <span className="text-[14px] text-fg-secondary">{cat.name}</span>
                <span className={"font-mono text-[12.5px] " + textToneFor(cat.pct)}>{cat.filled}/{cat.total}</span>
              </div>
              <Meter percent={cat.pct} tone={toneFor(cat.pct)} delayClass={"kora-d" + Math.min(6, i + 3)} />
            </div>
          ))}
        </div>

        {coverage.critical_missing_fields.length > 0 && (
          <div className="mt-[26px] border-t border-white/[0.055] pt-5">
            <SectionLabel className="mb-3">CRITICAL GAPS</SectionLabel>
            <div className="flex flex-wrap gap-2">
              {coverage.critical_missing_fields.map((gap) => <GapChip key={gap} label={gap} />)}
            </div>
          </div>
        )}
      </Panel>

      <Panel className="px-[26px] py-6">
        <h2 className="mb-1.5 text-[16px] font-semibold">Missing information by category</h2>
        <p className="m-0 mb-6 text-[13.5px] text-fg-dim">
          What to request for each gap, and why it matters — not just a list of field names.
        </p>

        {grouped.length === 0 ? (
          <div className="py-4 text-center text-[13.5px] text-fg-dim">Nothing missing — every checklist field was found.</div>
        ) : (
          grouped.map(([category, items]) => (
            <div key={category} className="mb-[22px] last:mb-0">
              <div className="mb-3 font-mono text-[10.5px] tracking-label text-accent-ghost">
                {(CATEGORY_LABELS[category] ?? category).toUpperCase()}
              </div>
              <div className="flex flex-col gap-[9px]">
                {items.map((item, i) => (
                  <div
                    key={item.field_name}
                    className={"flex items-baseline gap-3 " + (i < items.length - 1 ? "border-b border-white/[0.04] pb-[9px]" : "")}
                  >
                    <span className="w-[130px] shrink-0 font-mono text-[11.5px] text-fg-secondary">{humanizeFieldName(item.field_name)}</span>
                    <span className="text-[13.5px] text-fg-muted [text-wrap:pretty]">{item.recommended_request ?? "—"}</span>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </Panel>
    </div>
  );
}
