"use client";

import Link from "next/link";
import { Building2 } from "lucide-react";
import { useOrganizations } from "@/features/organizations/hooks";
import { CreateOrgDialog } from "@/features/organizations/components/create-org-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { format } from "date-fns";

export default function OrganizationsPage() {
  const { data: organizations, isLoading } = useOrganizations();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Organizations</h1>
          <p className="text-sm text-muted-foreground">Manage the organizations you belong to.</p>
        </div>
        <CreateOrgDialog />
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : !organizations || organizations.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No organizations yet"
          description="Create your first organization to start uploading documents."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {organizations.map((org) => (
            <Link key={org.id} href={`/organizations/${org.id}`}>
              <Card className="h-full border-border/50 transition-colors hover:border-primary/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    {org.name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">/{org.slug}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Created {format(new Date(org.created_at), "MMM d, yyyy")}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}