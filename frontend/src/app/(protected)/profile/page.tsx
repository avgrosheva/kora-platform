"use client";

import { format } from "date-fns";
import { toast } from "sonner";
import { useAuth } from "@/features/auth/auth-context";
import { Profile } from "@/components/kora/screens/Profile";

export default function ProfilePage() {
  const { user, logout } = useAuth();

  if (!user) {
    return <div className="relative z-10 p-9 text-sm text-fg-dim">Loading…</div>;
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
