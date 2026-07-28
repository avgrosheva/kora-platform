import type { MembershipRole } from "@/types/api";

export interface CreateOrgInput {
  name: string;
  slug?: string;
}

export interface AddMemberInput {
  user_id: string;
  role: MembershipRole;
}

export interface ChangeRoleInput {
  role: MembershipRole;
}

export interface InviteMemberInput {
  email: string;
  role: MembershipRole;
}

export interface InvitationRead {
  id: string;
  organization_id: string;
  email: string;
  role: MembershipRole;
  token: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
}