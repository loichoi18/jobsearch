"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { apiFetch } from "@/lib/api";
import { daysSince, needsFollowUp } from "@/lib/stats";
import { cn } from "@/lib/utils";
import { JOB_STATUSES, type Job, type JobStatus } from "@/lib/types";

const COLUMN_LABEL: Record<JobStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};

function JobCard({ job, dragging }: { job: Job; dragging?: boolean }) {
  const days = daysSince(job.updated_at ?? job.created_at);
  const followUp = needsFollowUp(job);
  return (
    <div
      className={cn(
        "rounded-md border bg-background p-3 shadow-sm",
        dragging && "opacity-90 shadow-md"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium leading-snug">{job.title}</p>
        {job.match_score != null && (
          <span className="gradient-text tnum shrink-0 text-sm font-bold">
            {Math.round(job.match_score)}
          </span>
        )}
      </div>
      {job.company && (
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          {job.company}
        </p>
      )}
      <div className="mt-2 flex items-center gap-2">
        {days !== null && (
          <span className="text-[11px] text-muted-foreground">
            {days === 0 ? "today" : `${days}d ago`}
          </span>
        )}
        {followUp && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">
            follow up?
          </span>
        )}
      </div>
    </div>
  );
}

function DraggableCard({ job }: { job: Job }) {
  const router = useRouter();
  const { attributes, listeners, setNodeRef, isDragging, transform } =
    useDraggable({ id: job.id });
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      role="button"
      tabIndex={0}
      aria-label={`${job.title} — ${COLUMN_LABEL[job.status]}`}
      onClick={() => {
        if (!isDragging) router.push(`/jobs/${job.id}`);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") router.push(`/jobs/${job.id}`);
      }}
      className={cn("cursor-grab focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md", isDragging && "opacity-40")}
      style={
        transform
          ? { transform: `translate(${transform.x}px, ${transform.y}px)` }
          : undefined
      }
    >
      <JobCard job={job} />
    </div>
  );
}

function Column({ status, jobs }: { status: JobStatus; jobs: Job[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex min-h-[240px] flex-col gap-2 rounded-xl bg-slate-100 p-2",
        isOver && "ring-2 ring-primary"
      )}
    >
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {COLUMN_LABEL[status]}
        </span>
        <span className="rounded-full bg-white px-2 text-xs tabular-nums text-slate-500">
          {jobs.length}
        </span>
      </div>
      {jobs.map((job) => (
        <DraggableCard key={job.id} job={job} />
      ))}
    </div>
  );
}

interface Props {
  jobs: Job[];
  onJobsChange: (jobs: Job[]) => void;
}

export function KanbanBoard({ jobs, onJobsChange }: Props) {
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const sensors = useSensors(
    // distance > 0 lets plain clicks through to the card's onClick
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor)
  );

  function onDragStart(event: DragStartEvent) {
    setActiveJob(jobs.find((j) => j.id === event.active.id) ?? null);
  }

  async function onDragEnd(event: DragEndEvent) {
    setActiveJob(null);
    const { active, over } = event;
    if (!over) return;
    const status = over.id as JobStatus;
    const job = jobs.find((j) => j.id === active.id);
    if (!job || job.status === status) return;

    // Optimistic move with rollback on failure
    const previous = jobs;
    onJobsChange(
      jobs.map((j) =>
        j.id === job.id
          ? {
              ...j,
              status,
              applied_at:
                status === "applied" && !j.applied_at
                  ? new Date().toISOString()
                  : j.applied_at,
              updated_at: new Date().toISOString(),
            }
          : j
      )
    );
    const res = await apiFetch(`/api/jobs/${job.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) {
      onJobsChange(previous);
      return;
    }
    // Reconcile with the server row (authoritative applied_at/updated_at)
    const updated: Job = await res.json();
    onJobsChange(
      previous.map((j) => (j.id === updated.id ? { ...j, ...updated } : j))
    );
  }

  return (
    <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {JOB_STATUSES.map((status) => (
          <Column
            key={status}
            status={status}
            jobs={jobs.filter((j) => j.status === status)}
          />
        ))}
      </div>
      <DragOverlay>
        {activeJob ? <JobCard job={activeJob} dragging /> : null}
      </DragOverlay>
    </DndContext>
  );
}
