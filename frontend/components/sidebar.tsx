"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Briefcase,
  FlaskConical,
  LayoutDashboard,
  Lightbulb,
  User,
} from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/profile", label: "Profile", icon: User },
  { href: "/evals", label: "Evals", icon: FlaskConical },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r bg-white">
      <div className="flex h-14 items-center gap-2 border-b px-4">
        <BarChart3 className="h-5 w-5 text-indigo-600" aria-hidden />
        <span className="font-semibold tracking-tight">JobPilot AU</span>
      </div>
      <nav className="flex flex-col gap-1 p-2" aria-label="Main">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative flex items-center gap-3 rounded-[8px] px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
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
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
