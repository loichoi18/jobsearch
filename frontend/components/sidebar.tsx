"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Briefcase,
  FlaskConical,
  LayoutDashboard,
  Lightbulb,
  Sparkles,
  User,
} from "lucide-react";

import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
  { href: "/jobs", labelKey: "nav.jobs", icon: Briefcase },
  { href: "/enhance", labelKey: "nav.enhance", icon: Sparkles },
  { href: "/insights", labelKey: "nav.insights", icon: Lightbulb },
  { href: "/profile", labelKey: "nav.profile", icon: User },
  { href: "/evals", labelKey: "nav.evals", icon: FlaskConical },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { t } = useI18n();

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r bg-card">
      <div className="flex h-14 items-center gap-2 border-b px-4">
        <BarChart3 className="h-5 w-5 text-primary" aria-hidden />
        <span className="font-semibold tracking-tight">{t("app.name")}</span>
      </div>
      <nav className="flex flex-col gap-1 p-2" aria-label="Main">
        {navItems.map(({ href, labelKey, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative flex items-center gap-3 rounded-[8px] px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {/* Active nav indicator: the one gradient accent in the shell */}
              {active && (
                <span
                  aria-hidden
                  className="brand-gradient absolute inset-y-1.5 left-0 w-1 rounded-full"
                />
              )}
              <Icon className="h-4 w-4" aria-hidden />
              {t(labelKey)}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
