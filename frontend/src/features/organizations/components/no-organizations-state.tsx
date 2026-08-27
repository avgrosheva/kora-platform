"use client";

import { useState } from "react";
import { Building2, Plus } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateOrgDialog } from "./create-org-dialog";

/**
 * Shown wherever a screen needs an organization to render anything, but
 * the user belongs to none yet. `primary` renders the full first-run
 * onboarding treatment; the default, more compact form is for
 * secondary org-scoped screens (Documents, Members, Settings) reached
 * directly. Still shadcn-styled -- used only by screens not yet on the
 * new visual system; Portfolio's onboarding now renders `NoOrganizations`
 * from `components/kora` directly.
 */
export function NoOrganizationsState({ primary = false }: { primary?: boolean }) {
  const [createOpen, setCreateOpen] = useState(false);

  if (primary) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Building2 className="h-6 w-6 text-primary" />
        </div>
        <h1 className="text-xl font-semibold tracking-tight">
          Create your first organization to get started
        </h1>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          Kora turns company documents into structured, evidence-backed due-diligence
          profiles. Everything you upload lives inside an organization, so create one to
          begin.
        </p>
        <div className="mt-6">
          <Button size="lg" className="gap-2" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" />
            Create organization
          </Button>
        </div>
        <CreateOrgDialog open={createOpen} onOpenChange={setCreateOpen} />
      </div>
    );
  }

  return (
    <div className="relative z-10 p-6">
      <EmptyState
        icon={Building2}
        title="No organization selected"
        description="Create an organization to start uploading and analyzing companies."
        action={
          <button type="button" onClick={() => setCreateOpen(true)} className={buttonVariants()}>
            <Plus className="mr-2 h-4 w-4" />
            Create organization
          </button>
        }
      />
      <CreateOrgDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
