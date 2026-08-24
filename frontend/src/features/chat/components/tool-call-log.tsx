import { Wrench } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ToolCallRecord } from "@/types/api";

const TOOL_LABELS: Record<string, string> = {
  search_document_chunks: "Searched documents",
  get_financial_time_series: "Fetched time series",
  calculate_metric: "Calculated metric",
  get_missing_information: "Checked missing info",
};

export function ToolCallLog({ toolCalls }: { toolCalls: ToolCallRecord[] }) {
  if (toolCalls.length === 0) return null;

  return (
    <div className="rounded-md border border-border/50 bg-accent/20 p-3">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Wrench className="h-3 w-3" />
        {toolCalls.length} tool call{toolCalls.length > 1 ? "s" : ""}
      </p>
      <ScrollArea className="max-h-32">
        <ul className="space-y-1.5">
          {toolCalls.map((call, i) => (
            <li key={i} className="text-xs">
              <span className="font-medium">{TOOL_LABELS[call.tool_name] ?? call.tool_name}</span>
              <span className="text-muted-foreground">: {call.result_summary}</span>
            </li>
          ))}
        </ul>
      </ScrollArea>
    </div>
  );
}