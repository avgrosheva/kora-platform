"use client";

import { format } from "date-fns";
import { toast } from "sonner";
import { useAuth } from "@/features/auth/auth-context";
import { Profile } from "@/components/kora/screens/Profile";
import { PageLoading } from "@/components/kora/primitives";

export default function ProfilePage() {
  const { user, logout } = useAuth();

  if (!user) {
    return <PageLoading />;
  }

  return (
    <Profile
      user={{
        email: user.email,
        fullName: user.full_name,
        createdAt: format(new Date(user.created_at), "PPP"),
        isActive: user.is_active,
      }}
      onLogout={() => {
        logout();
        toast.success("Logged out.");
      }}
    />
  );
}
