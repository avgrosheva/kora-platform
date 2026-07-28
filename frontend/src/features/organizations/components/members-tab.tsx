"use client";

import { MoreHorizontal, UserMinus } from "lucide-react";
import { toast } from "sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { RoleBadge } from "@/components/shared/role-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { Users } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-context";
import { useChangeRole, useMembers, useRemoveMember } from "../hooks";
import type { MembershipRole } from "@/types/api";

const ASSIGNABLE_ROLES: MembershipRole[] = ["owner", "admin", "member"];

export function MembersTab({ organizationId }: { organizationId: string }) {
  const { user } = useAuth();
  const { data: members, isLoading } = useMembers(organizationId);
  const changeRole = useChangeRole(organizationId);
  const removeMember = useRemoveMember(organizationId);

  if (isLoading) {
    return <Skeleton className="h-48" />;
  }

  if (!members || members.length === 0) {
    return <EmptyState icon={Users} title="No members" />;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>User ID</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>Joined</TableHead>
          <TableHead className="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {members.map((member) => (
          <TableRow key={member.id}>
            <TableCell className="font-mono text-xs">
              {member.user_id.slice(0, 8)}…
              {member.user_id === user?.id && (
                <span className="ml-2 text-xs text-muted-foreground">(you)</span>
              )}
            </TableCell>
            <TableCell>
              <RoleBadge role={member.role} />
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {new Date(member.created_at).toLocaleDateString()}
            </TableCell>
            <TableCell>
              <DropdownMenu>
                <DropdownMenuTrigger className="rounded-md p-1.5 hover:bg-accent">
                  <MoreHorizontal className="h-4 w-4" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {ASSIGNABLE_ROLES.filter((r) => r !== member.role).map((role) => (
                    <DropdownMenuItem
                      key={role}
                      onClick={() =>
                        changeRole.mutate(
                          { userId: member.user_id, input: { role } },
                          {
                            onSuccess: () => toast.success(`Role updated to ${role}.`),
                            onError: (e) => toast.error(e.message),
                          }
                        )
                      }
                    >
                      Make {role}
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() =>
                      removeMember.mutate(member.user_id, {
                        onSuccess: () => toast.success("Member removed."),
                        onError: (e) => toast.error(e.message),
                      })
                    }
                  >
                    <UserMinus className="mr-2 h-4 w-4" />
                    Remove
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}