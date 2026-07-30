"use client";

import { useMutation } from "@tanstack/react-query";
import { chatApi } from "./api";

export function useAskChat() {
  return useMutation({
    mutationFn: ({ organizationId, question }: { organizationId: string; question: string }) =>
      chatApi.ask(organizationId, question),
  });
}