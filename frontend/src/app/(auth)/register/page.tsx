"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { registerSchema, type RegisterFormValues } from "@/features/auth/schemas";
import { authApi } from "@/features/auth/api";
import { useLoginMutation } from "@/features/auth/hooks";
import { FlowLines } from "@/components/kora/FlowLines";
import { FieldLabel, Kicker, Panel, PrimaryButton } from "@/components/kora/primitives";

const field =
  "w-full rounded-[9px] border border-white/[0.09] bg-white/[0.025] px-[13px] py-[11px] text-[13px] text-fg-secondary outline-none transition-colors focus:border-accent/35";

export default function RegisterPage() {
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });
  const loginMutation = useLoginMutation();

  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: () => {
      const { email, password } = getValues();
      loginMutation.mutate(
        { email, password },
        { onError: () => toast.error("Registered, but automatic login failed. Please sign in.") }
      );
    },
    onError: (error) => toast.error(error.message || "Registration failed."),
  });

  const onSubmit = (values: RegisterFormValues) => {
    registerMutation.mutate({
      email: values.email,
      password: values.password,
      full_name: values.full_name || undefined,
    });
  };

  const isPending = registerMutation.isPending || loginMutation.isPending;

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-ink-950 px-4 font-sans text-fg">
      <FlowLines />
      <Panel className="kora-rise relative z-10 w-full max-w-sm px-8 py-9">
        <Kicker>KORA</Kicker>
        <h1 className="m-0 mb-1.5 text-[22px] font-semibold tracking-tight">Create account</h1>
        <p className="m-0 mb-6 text-[13px] text-fg-dim">Sign up for Kora.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-[18px]">
          <div>
            <FieldLabel>EMAIL</FieldLabel>
            <input id="email" type="email" autoComplete="email" className={field} {...register("email")} />
            {errors.email && (
              <p className="mt-1.5 text-[11.5px] text-danger-soft">{errors.email.message}</p>
            )}
          </div>
          <div>
            <FieldLabel>FULL NAME (OPTIONAL)</FieldLabel>
            <input id="full_name" className={field} {...register("full_name")} />
          </div>
          <div>
            <FieldLabel>PASSWORD</FieldLabel>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              className={field}
              {...register("password")}
            />
            {errors.password && (
              <p className="mt-1.5 text-[11.5px] text-danger-soft">{errors.password.message}</p>
            )}
          </div>
          <PrimaryButton
            type="submit"
            className={"mt-1 w-full text-center" + (isPending ? " pointer-events-none opacity-50" : "")}
          >
            {isPending ? "CREATING ACCOUNT…" : "CREATE ACCOUNT"}
          </PrimaryButton>
        </form>

        <p className="m-0 mt-6 text-center text-[12.5px] text-fg-dim">
          Already have an account?{" "}
          <a href="/login" className="text-accent-pale hover:underline">
            Sign in
          </a>
        </p>
      </Panel>
    </div>
  );
}
