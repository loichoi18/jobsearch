"use client";

import { Monitor, Moon, Sun } from "lucide-react";

import { useI18n } from "@/lib/i18n";
import { useTheme, type ThemeSetting } from "@/lib/theme";
import { cn } from "@/lib/utils";

const OPTIONS: { value: ThemeSetting; icon: typeof Sun; labelKey: string }[] = [
  { value: "light", icon: Sun, labelKey: "theme.light" },
  { value: "dark", icon: Moon, labelKey: "theme.dark" },
  { value: "system", icon: Monitor, labelKey: "theme.system" },
];

export function ThemeToggle() {
  const { setting, setSetting } = useTheme();
  const { t } = useI18n();

  return (
    <div
      role="group"
      aria-label={t("settings.theme")}
      className="flex items-center gap-0.5 rounded-[8px] border bg-muted p-0.5"
    >
      {OPTIONS.map(({ value, icon: Icon, labelKey }) => {
        const active = setting === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => setSetting(value)}
            aria-pressed={active}
            title={t(labelKey)}
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-[6px] transition-colors",
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" aria-hidden />
            <span className="sr-only">{t(labelKey)}</span>
          </button>
        );
      })}
    </div>
  );
}
