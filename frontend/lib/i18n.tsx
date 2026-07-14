"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type Locale = "en" | "vi";

const STORAGE_KEY = "jobpilot-locale";

/** Flat key → string. Add keys here as more of the UI is localised. */
const dictionaries: Record<Locale, Record<string, string>> = {
  en: {
    "app.name": "JobPilot AU",
    "nav.dashboard": "Dashboard",
    "nav.jobs": "Jobs",
    "nav.enhance": "Enhance CV",
    "nav.insights": "Insights",
    "nav.profile": "Profile",
    "nav.evals": "Evals",
    "topbar.signOut": "Sign out",
    "settings.language": "Language",
    "settings.theme": "Theme",
    "theme.light": "Light",
    "theme.dark": "Dark",
    "theme.system": "System",
    "enhance.title": "Enhance CV",
    "enhance.subtitle":
      "Rebuild your resume against a job description for a 90%+ ATS score.",
    "enhance.companyLabel": "Company name",
    "enhance.companyPlaceholder": "e.g. Atlassian",
    "enhance.resumeLabel": "Your resume",
    "enhance.resumePlaceholder": "Paste your current resume text here…",
    "enhance.jdLabel": "Job description",
    "enhance.jdPlaceholder": "Paste the job description here…",
    "enhance.submit": "Enhance my resume",
    "enhance.submitting": "Enhancing…",
    "enhance.resultTitle": "Rewritten resume + rejection risks",
    "enhance.copy": "Copy",
    "enhance.copied": "Copied",
    "enhance.error": "Something went wrong. Please try again.",
    "enhance.required": "Fill in all three fields first.",
  },
  vi: {
    "app.name": "JobPilot AU",
    "nav.dashboard": "Bảng điều khiển",
    "nav.jobs": "Việc làm",
    "nav.enhance": "Cải thiện CV",
    "nav.insights": "Phân tích",
    "nav.profile": "Hồ sơ",
    "nav.evals": "Đánh giá",
    "topbar.signOut": "Đăng xuất",
    "settings.language": "Ngôn ngữ",
    "settings.theme": "Giao diện",
    "theme.light": "Sáng",
    "theme.dark": "Tối",
    "theme.system": "Hệ thống",
    "enhance.title": "Cải thiện CV",
    "enhance.subtitle":
      "Viết lại CV theo mô tả công việc để đạt điểm ATS trên 90%.",
    "enhance.companyLabel": "Tên công ty",
    "enhance.companyPlaceholder": "ví dụ: Atlassian",
    "enhance.resumeLabel": "CV của bạn",
    "enhance.resumePlaceholder": "Dán nội dung CV hiện tại của bạn vào đây…",
    "enhance.jdLabel": "Mô tả công việc",
    "enhance.jdPlaceholder": "Dán mô tả công việc vào đây…",
    "enhance.submit": "Cải thiện CV của tôi",
    "enhance.submitting": "Đang xử lý…",
    "enhance.resultTitle": "CV đã viết lại + rủi ro bị loại",
    "enhance.copy": "Sao chép",
    "enhance.copied": "Đã sao chép",
    "enhance.error": "Đã xảy ra lỗi. Vui lòng thử lại.",
    "enhance.required": "Vui lòng điền cả ba trường trước.",
  },
};

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
    if (stored === "en" || stored === "vi") setLocaleState(stored);
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.lang = next === "vi" ? "vi" : "en-AU";
  }, []);

  const t = useCallback(
    (key: string) => dictionaries[locale][key] ?? dictionaries.en[key] ?? key,
    [locale]
  );

  const value = useMemo(
    () => ({ locale, setLocale, t }),
    [locale, setLocale, t]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

/** Convenience hook returning just the translate function. */
export function useT(): (key: string) => string {
  return useI18n().t;
}
