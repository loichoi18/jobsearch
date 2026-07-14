"use client";

import { useRouter } from "next/navigation";

import { LanguageToggle } from "@/components/language-toggle";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useUser } from "@/hooks/use-user";
import { useI18n } from "@/lib/i18n";
import { createClient } from "@/lib/supabase/client";

export function Topbar({ title }: { title?: string }) {
  const { user } = useUser();
  const router = useRouter();
  const { t } = useI18n();

  async function signOut() {
    await createClient().auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-6">
      <h1 className="text-sm font-medium text-muted-foreground">
        {title ?? t("app.name")}
      </h1>
      <div className="flex items-center gap-3">
        <LanguageToggle />
        <ThemeToggle />
        {user && (
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {user.email}
          </span>
        )}
        <Button variant="ghost" size="sm" onClick={signOut}>
          {t("topbar.signOut")}
        </Button>
      </div>
    </header>
  );
}
