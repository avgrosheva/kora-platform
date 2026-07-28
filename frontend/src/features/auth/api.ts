import { apiClient } from "@/lib/api-client";
import type { TokenResponse, UserRead } from "@/types/api";
import type { LoginCredentials, RegisterInput } from "./types";

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>("/auth/login", credentials);
    return data;
  },

  register: async (input: RegisterInput): Promise<UserRead> => {
    const { data } = await apiClient.post<UserRead>("/auth/register", input);
    return data;
  },

  me: async (): Promise<UserRead> => {
    const { data } = await apiClient.get<UserRead>("/auth/me");
    return data;
  },
};