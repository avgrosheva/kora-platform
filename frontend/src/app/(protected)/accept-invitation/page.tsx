"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import { organizationsApi } from "@/features/organizations/api";
import { ApiError } from "@/lib/api-client";
import { AcceptInvitation, type AcceptInvitationStatus } from "@/components/kora/screens/AcceptInvitation";

type Result = { ok: true } | { ok: false; message: string };

// Module-level, keyed by token, rather than component state: this
// page's effect can run its accept call, then have the whole component
// torn down and remounted -- observed both from React StrictMode's
// dev-mode double-invoke, and from a remount seemingly triggered by
// this very call's own organizations-list invalidation cascading
// through the org-scoped layout above it -- more than once before the
// request settles. A ref/state guard scoped to one component instance
// doesn't survive that (it silently drops the resolved result on an
// instance nobody's looking at anymore, leaving the UI stuck on
// "pending" forever even though the accept succeeded server-side). A
// module-level cache does survive it, since it lives for the module's
// lifetime -- a real page navigation -- not any one component instance.
const acceptRequests = new Map<string, Promise<Result>>();

function acceptOnce(token: string): Promise<Result> {
  let promise = acceptRequests.get(token);
  if (!promise) {
    promise = organizationsApi
      .acceptInvitation(token)
      .then((): Result => ({ ok: true }))
      .catch((error): Result => ({
        ok: false,
        message: error instanceof ApiError ? error.message : "Could not accept invitation.",
      }));
    acceptRequests.set(token, promise);
  }
  return promise;
}

export default function AcceptInvitationPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const token = searchParams.get("token");
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    acceptOnce(token).then((r) => {
      if (cancelled) return;
      setResult(r);
      if (r.ok) queryClient.invalidateQueries({ queryKey: ["organizations"] });
    });
    return () => {
      cancelled = true;
    };
  }, [token, queryClient]);

  const status: AcceptInvitationStatus = !token
    ? "no-token"
    : result === null
      ? "pending"
      : result.ok
        ? "success"
        : "error";

  return (
    <AcceptInvitation
      status={status}
      errorMessage={result && !result.ok ? result.message : undefined}
      onGoToPortfolio={() => router.push("/portfolio")}
    />
  );
}
