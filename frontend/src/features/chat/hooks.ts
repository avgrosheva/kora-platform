"use client";

import { useMutation } from "@tanstack/react-query";
import { chatApi } from "./api";

export function useAskChat() {
  return useMutation({
    mutationFn: ({ organizationId, question }: { organizationId: string; question: string }) =>
      chatApi.ask(organizationId, question),
  });
}

export function useAskChatV2() {
  return useMutation({
    mutationFn: ({
      organizationId,
      question,
      documentId,
    }: {
      organizationId: string;
      question: string;
      documentId?: string;
    }) => chatApi.askV2(organizationId, question, documentId),
  });
}