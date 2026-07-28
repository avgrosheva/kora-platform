"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { Building2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { useOrganization, useDeleteOrganization } from "@/features/organizations/hooks";
import { MembersTab } from "@/features/organizations/components/members-tab";
import { InvitationsTab } from "@/features/organizations/components/invitations-tab";

export default function OrganizationDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { data: organization, isLoading, isError } = useOrganization(params.id);
  const deleteOrg = useDeleteOrganization();
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (isLoading) {
    return <Skeleton className="h-96" />;
  }

  if (isError || !organization) {
    return (
      <EmptyState
        icon={Building2}
        title="Organization not found"
        description="It may not exist, or you may not have access to it."
      />
    );
  }

  const handleDelete = () => {
    deleteOrg.mutate(organization.id, {
      onSuccess: () => {
        toast.success("Organization deleted.");
        router.push("/organizations");
      },
      onError: (error) => toast.error(error.message || "Could not delete organization."),
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <Building2 className="h-5 w-5 text-muted-foreground" />
            {organization.name}
          </h1>
          <p className="text-sm text-muted-foreground">/{organization.slug}</p>
        </div>

        <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
            <AlertDialogTrigger className="inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium bg-destructive text-destructive-foreground">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
            </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this organization?</AlertDialogTitle>
              <AlertDialogDescription>
                This permanently deletes the organization, its documents, and all associated
                data. This action cannot be undone. Only the organization owner can do this.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDelete} className="bg-destructive">
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      <Tabs defaultValue="members">
        <TabsList>
          <TabsTrigger value="members">Members</TabsTrigger>
          <TabsTrigger value="invitations">Invitations</TabsTrigger>
        </TabsList>
        <TabsContent value="members" className="mt-4">
          <MembersTab organizationId={organization.id} />
        </TabsContent>
        <TabsContent value="invitations" className="mt-4">
          <InvitationsTab organizationId={organization.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}