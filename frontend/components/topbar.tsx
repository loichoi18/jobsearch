"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useUser } from "@/hooks/use-user";
import { createClient } from "@/lib/supabase/client";

export function Topbar({ title }: { title?: string }) {
  const { user } = useUser();
  const router = useRouter();

  async function signOut() {
    await createClient().auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <header className="flex h-14 items-center justify-between border-b bg-white px-6">
      <h1 className="text-sm font-medium text-muted-foreground">
        {title ?? "JobPilot AU"}
      </h1>
      <div className="flex items-center gap-3">
        {user && (
          <span className="text-sm text-muted-foreground">{user.email}</span>
        )}
        <Button variant="ghost" size="sm" onClick={signOut}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
