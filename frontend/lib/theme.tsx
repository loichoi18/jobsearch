"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type ThemeSetting = "light" | "dark" | "system";

const STORAGE_KEY = "jobpilot-theme";

type ThemeContextValue = {
  /** The user's chosen setting, including "system". */
  setting: ThemeSetting;
  /** The theme actually applied right now ("light" | "dark"). */
  resolved: "light" | "dark";
  setSetting: (setting: ThemeSetting) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function systemPrefersDark(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
}

function resolve(setting: ThemeSetting): "light" | "dark" {
  if (setting === "system") return systemPrefersDark() ? "dark" : "light";
  return setting;
}

function apply(resolved: "light" | "dark") {
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
}

/** Runs before React hydrates (see app/layout.tsx) to set the class with no
 * flash of the wrong theme. Kept in sync with resolve()/apply() above. */
export const themeInitScript = `(function(){try{var s=localStorage.getItem("${STORAGE_KEY}")||"system";var d=s==="dark"||(s==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);var r=document.documentElement;r.classList.toggle("dark",d);r.style.colorScheme=d?"dark":"light";}catch(e){}})();`;

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [setting, setSettingState] = useState<ThemeSetting>("system");
  const [resolved, setResolved] = useState<"light" | "dark">("light");

  // Adopt the stored preference after mount (the init script already painted it).
  useEffect(() => {
    const stored =
      (localStorage.getItem(STORAGE_KEY) as ThemeSetting | null) ?? "system";
    setSettingState(stored);
    setResolved(resolve(stored));
  }, []);

  // Follow OS changes while on "system".
  useEffect(() => {
    if (setting !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const next = mq.matches ? "dark" : "light";
      setResolved(next);
      apply(next);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [setting]);

  const setSetting = useCallback((next: ThemeSetting) => {
    setSettingState(next);
    localStorage.setItem(STORAGE_KEY, next);
    const r = resolve(next);
    setResolved(r);
    apply(r);
  }, []);

  const value = useMemo(
    () => ({ setting, resolved, setSetting }),
    [setting, resolved, setSetting]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
