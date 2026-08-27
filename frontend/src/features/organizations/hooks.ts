"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { organizationsApi } from "./api";
import type {
  AddMemberInput,
  ChangeRoleInput,
  CreateOrgInput,
  InviteMemberInput,
  UpdateOrgInput,
} from "./types";

export function useOrganizations() {
  return useQuery({
    queryKey: ["organizations"],
    queryFn: organizationsApi.list,
  });
}

export function useOrganization(organizationId: string | undefined) {
  return useQuery({
    queryKey: ["organizations", organizationId],
    queryFn: () => organizationsApi.get(organizationId as string),
    enabled: !!organizationId,
  });
}

export function useCreateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateOrgInput) => organizationsApi.create(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}

export function useUpdateOrganization(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateOrgInput) => organizationsApi.update(organizationId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
      queryClient.invalidateQueries({ queryKey: ["organizations", organizationId] });
    },
  });
}

export function useDeleteOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (organizationId: string) => organizationsApi.delete(organizationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}

export function useMembers(organizationId: string | undefined) {
  return useQuery({
    queryKey: ["organizations", organizationId, "members"],
    queryFn: () => organizationsApi.listMembers(organizationId as string),
    enabled: !!organizationId,
  });
}

export function useAddMember(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AddMemberInput) => organizationsApi.addMember(organizationId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations", organizationId, "members"] });
    },
  });
}

export function useRemoveMember(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => organizationsApi.removeMember(organizationId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations", organizationId, "members"] });
    },
  });
}

export function useChangeRole(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, input }: { userId: string; input: ChangeRoleInput }) =>
      organizationsApi.changeRole(organizationId, userId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations", organizationId, "members"] });
    },
  });
}

export function useInvitations(organizationId: string | undefined) {
  return useQuery({
    queryKey: ["organizations", organizationId, "invitations"],
    queryFn: () => organizationsApi.listInvitations(organizationId as string),
    enabled: !!organizationId,
  });
}

export function useInviteMember(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: InviteMemberInput) => organizationsApi.inviteMember(organizationId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["organizations", organizationId, "invitations"],
      });
    },
  });
}

export function useAcceptInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => organizationsApi.acceptInvitation(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}