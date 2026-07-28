import { Badge } from "@/components/ui/badge";
import type { MembershipRole } from "@/types/api";

const ROLE_LABELS: Record<MembershipRole, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
};

const ROLE_VARIANTS: Record<MembershipRole, "default" | "secondary" | "outline"> = {
  owner: "default",
  admin: "secondary",
  member: "outline",
};

export function RoleBadge({ role }: { role: MembershipRole }) {
  return <Badge variant={ROLE_VARIANTS[role]}>{ROLE_LABELS[role]}</Badge>;
}