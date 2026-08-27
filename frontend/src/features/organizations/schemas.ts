import { z } from "zod";

export const createOrgSchema = z.object({
  name: z.string().min(1, "Name is required.").max(255),
  slug: z
    .string()
    .max(255)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Lowercase letters, numbers, and hyphens only.")
    .optional()
    .or(z.literal("")),
});

export type CreateOrgFormValues = z.infer<typeof createOrgSchema>;

export const updateOrgSchema = z.object({
  name: z.string().min(1, "Name is required.").max(255),
  slug: z
    .string()
    .min(1, "Slug is required.")
    .max(255)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Lowercase letters, numbers, and hyphens only."),
});

export type UpdateOrgFormValues = z.infer<typeof updateOrgSchema>;

export const inviteMemberSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  role: z.enum(["owner", "admin", "member"]),
});

export type InviteMemberFormValues = z.infer<typeof inviteMemberSchema>;