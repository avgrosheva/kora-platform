"use client";

import { Mail, Copy } from "lucide-react";
import { toast } from "sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RoleBadge } from "@/components/shared/role-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InviteMemberDialog } from "./invite-member-dialog";
import { useInvitations } from "../hooks";

export function InvitationsTab({ organizationId }: { organizationId: string }) {
  const { data: invitations, isLoading } = useInvitations(organizationId);

  const copyLink = (token: string) => {
    const url = `${window.location.origin}/accept-invitation?token=${token}`;
    navigator.clipboard.writeText(url);
    toast.success("Invitation link copied.");
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <InviteMemberDialog organizationId={organizationId} />
      </div>

      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !invitations || invitations.length === 0 ? (
        <EmptyState icon={Mail} title="No pending invitations" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Expires</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {invitations.map((invitation) => {
              const expired = new Date(invitation.expires_at) < new Date();
              return (
                <TableRow key={invitation.id}>
                  <TableCell>{invitation.email}</TableCell>
                  <TableCell>
                    <RoleBadge role={invitation.role} />
                  </TableCell>
                  <TableCell>
                    {invitation.accepted_at ? (
                      <Badge variant="default">Accepted</Badge>
                    ) : expired ? (
                      <Badge variant="destructive">Expired</Badge>
                    ) : (
                      <Badge variant="secondary">Pending</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {new Date(invitation.expires_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {!invitation.accepted_at && !expired && (
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => copyLink(invitation.token)}
                        title="Copy invitation link"
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
}