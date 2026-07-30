"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { registerSchema, type RegisterFormValues } from "@/features/auth/schemas";
import { authApi } from "@/features/auth/api";
import { useLoginMutation } from "@/features/auth/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useMutation } from "@tanstack/react-query";

export default function RegisterPage() {
  const router = useRouter();
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
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm border-border/50">
        <CardHeader>
          <CardTitle className="text-2xl font-semibold tracking-tight">Create account</CardTitle>
          <CardDescription>Sign up for Kora</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" {...register("email")} />
              {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="full_name">Full name (optional)</Label>
              <Input id="full_name" {...register("full_name")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? "Creating account…" : "Create account"}
            </Button>
          </form>
          <p className="mt-4 text-center text-xs text-muted-foreground">
            Already have an account?{" "}
            <a href="/login" className="text-primary hover:underline">
              Sign in
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}