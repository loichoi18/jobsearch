import { cn } from "@/lib/utils";
import type { JobStatus } from "@/lib/types";

const STYLES: Record<JobStatus, string> = {
  saved: "bg-slate-100 text-slate-700",
  applied: "bg-blue-100 text-blue-700",
  interview: "bg-amber-100 text-amber-700",
  offer: "bg-emerald-100 text-emerald-700",
  rejected: "bg-red-100 text-red-700",
};

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        STYLES[status]
      )}
    >
      {status}
    </span>
  );
}
