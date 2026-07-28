import { apiClient } from "@/lib/api-client";
import type { MembershipRead, OrganizationRead } from "@/types/api";
import type {
  AddMemberInput,
  ChangeRoleInput,
  CreateOrgInput,
  InvitationRead,
  InviteMemberInput,
} from "./types";

export const organizationsApi = {
  list: async (): Promise<OrganizationRead[]> => {
    const { data } = await apiClient.get<OrganizationRead[]>("/organizations");
    return data;
  },

  get: async (organizationId: string): Promise<OrganizationRead> => {
    const { data } = await apiClient.get<OrganizationRead>(`/organizations/${organizationId}`);
    return data;
  },

  create: async (input: CreateOrgInput): Promise<OrganizationRead> => {
    const { data } = await apiClient.post<OrganizationRead>("/organizations", {
      name: input.name,
      slug: input.slug || undefined,
    });
    return data;
  },

  delete: async (organizationId: string): Promise<void> => {
    await apiClient.delete(`/organizations/${organizationId}`);
  },

  listMembers: async (organizationId: string): Promise<MembershipRead[]> => {
    const { data } = await apiClient.get<MembershipRead[]>(
      `/organizations/${organizationId}/members`
    );
    return data;
  },

  addMember: async (organizationId: string, input: AddMemberInput): Promise<MembershipRead> => {
    const { data } = await apiClient.post<MembershipRead>(
      `/organizations/${organizationId}/members`,
      input
    );
    return data;
  },

  removeMember: async (organizationId: string, userId: string): Promise<void> => {
    await apiClient.delete(`/organizations/${organizationId}/members/${userId}`);
  },

  changeRole: async (
    organizationId: string,
    userId: string,
    input: ChangeRoleInput
  ): Promise<MembershipRead> => {
    const { data } = await apiClient.patch<MembershipRead>(
      `/organizations/${organizationId}/members/${userId}`,
      input
    );
    return data;
  },

  listInvitations: async (organizationId: string): Promise<InvitationRead[]> => {
    const { data } = await apiClient.get<InvitationRead[]>(
      `/organizations/${organizationId}/invitations`
    );
    return data;
  },

  inviteMember: async (
    organizationId: string,
    input: InviteMemberInput
  ): Promise<InvitationRead> => {
    const { data } = await apiClient.post<InvitationRead>(
      `/organizations/${organizationId}/invitations`,
      input
    );
    return data;
  },

  acceptInvitation: async (token: string): Promise<MembershipRead> => {
    const { data } = await apiClient.post<MembershipRead>(
      `/organizations/invitations/${token}/accept`
    );
    return data;
  },
};