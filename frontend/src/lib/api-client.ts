/**
 * Typed API client wrapping axios, with JWT auth injection and a
 * normalized error shape. All feature `api.ts` files call through this
 * client rather than using axios/fetch directly.
 */

import axios, { AxiosError, type AxiosInstance } from "axios";
import { env } from "./env";
import type { ApiErrorBody } from "@/types/api";

const TOKEN_STORAGE_KEY = "kora_access_token";

export class ApiError extends Error {
  readonly status: number;
  readonly errorType?: string;
  readonly requestId?: string;

  constructor(status: number, message: string, errorType?: string, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorType = errorType;
    this.requestId = requestId;
  }
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

function createClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: `${env.apiBaseUrl}/api/v1`,
    timeout: 60_000,
  });

  instance.interceptors.request.use((config) => {
    const token = getStoredToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError<ApiErrorBody>) => {
      const status = error.response?.status ?? 0;
      const body = error.response?.data;

      let message = "An unexpected error occurred.";
      if (body?.detail) {
        message =
          typeof body.detail === "string"
            ? body.detail
            : body.detail.map((d) => d.msg).join("; ");
      } else if (error.message) {
        message = error.message;
      }

      if (status === 401 && typeof window !== "undefined") {
        setStoredToken(null);
        if (!window.location.pathname.startsWith("/login")) {
          window.location.href = "/login";
        }
      }

      return Promise.reject(
        new ApiError(status, message, body?.error_type, body?.request_id)
      );
    }
  );

  return instance;
}

export const apiClient = createClient();