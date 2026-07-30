import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(8, "At least 8 characters.").max(128),
  full_name: z.string().max(255).optional(),
});

export type RegisterFormValues = z.infer<typeof registerSchema>;