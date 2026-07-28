"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { useAcceptInvitation } from "@/features/organizations/hooks";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function AcceptInvitationPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");
  const acceptInvitation = useAcceptInvitation();

  useEffect(() => {
    if (token && acceptInvitation.isIdle) {
      acceptInvitation.mutate(token);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-sm border-border/50">
        <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
          {!token ? (
            <>
              <XCircle className="h-10 w-10 text-destructive" />
              <p className="text-sm">No invitation token provided.</p>
            </>
          ) : acceptInvitation.isPending || acceptInvitation.isIdle ? (
            <>
              <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Accepting invitation…</p>
            </>
          ) : acceptInvitation.isSuccess ? (
            <>
              <CheckCircle2 className="h-10 w-10 text-emerald-500" />
              <p className="text-sm">You've joined the organization.</p>
              <Button onClick={() => router.push("/organizations")}>Go to organizations</Button>
            </>
          ) : (
            <>
              <XCircle className="h-10 w-10 text-destructive" />
              <p className="text-sm">{acceptInvitation.error?.message || "Could not accept invitation."}</p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}