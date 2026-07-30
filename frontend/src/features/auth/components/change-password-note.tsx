import { Info } from "lucide-react";

export function ChangePasswordNote() {
  return (
    <div className="flex items-start gap-2 rounded-md border border-border/50 bg-accent/30 p-4 text-sm text-muted-foreground">
      <Info className="mt-0.5 h-4 w-4 shrink-0" />
      <p>
        Password changes and profile editing aren't available yet — the backend doesn't
        currently expose an endpoint for updating account details.
      </p>
    </div>
  );
}