"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAcceptInvitation } from "@/features/organizations/hooks";
import { AcceptInvitation, type AcceptInvitationStatus } from "@/components/kora/screens/AcceptInvitation";

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

  const status: AcceptInvitationStatus = !token
    ? "no-token"
    : acceptInvitation.isPending || acceptInvitation.isIdle
      ? "pending"
      : acceptInvitation.isSuccess
        ? "success"
        : "error";

  return (
    <AcceptInvitation
      status={status}
      errorMessage={acceptInvitation.error?.message}
      onGoToPortfolio={() => router.push("/portfolio")}
    />
  );
}
