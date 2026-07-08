"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { AU_LOCATIONS } from "@/lib/locations";
import { cn } from "@/lib/utils";
import type { Profile } from "@/lib/types";

interface ProfileFormProps {
  value: Profile;
  onSave: (profile: Profile) => Promise<void>;
  saving: boolean;
}

const toLines = (items: string[]) => items.join("\n");
const fromLines = (text: string) =>
  text.split("\n").map((s) => s.trim()).filter(Boolean);
const toComma = (items: string[]) => items.join(", ");
const fromComma = (text: string) =>
  text.split(",").map((s) => s.trim()).filter(Boolean);

export function ProfileForm({ value, onSave, saving }: ProfileFormProps) {
  const [p, setP] = useState<Profile>(value);
  const set = (patch: Partial<Profile>) => setP({ ...p, ...patch });

  return (
    <form
      className="space-y-6"
      onSubmit={(e) => {
        e.preventDefault();
        void onSave(p);
      }}
    >
      <Card>
        <CardHeader>
          <CardTitle>Personal information</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="name">Full name</Label>
            <Input
              id="name"
              value={p.name ?? ""}
              onChange={(e) => set({ name: e.target.value || null })}
              placeholder="e.g. Jane Nguyen"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={p.email ?? ""}
              onChange={(e) => set({ email: e.target.value || null })}
              placeholder="jane@example.com"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="phone">Phone</Label>
            <Input
              id="phone"
              value={p.phone ?? ""}
              onChange={(e) => set({ phone: e.target.value || null })}
              placeholder="+61 4XX XXX XXX"
            />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <Label>Preferred locations</Label>
            <div className="flex flex-wrap gap-2">
              {AU_LOCATIONS.map((loc) => {
                const active = p.preferred_locations.includes(loc);
                return (
                  <button
                    key={loc}
                    type="button"
                    aria-pressed={active}
                    onClick={() =>
                      set({
                        preferred_locations: active
                          ? p.preferred_locations.filter((l) => l !== loc)
                          : [...p.preferred_locations, loc],
                      })
                    }
                    className={cn(
                      "rounded-full border px-3 py-1 text-sm transition",
                      active
                        ? "border-indigo-600 bg-indigo-600 text-white"
                        : "border-slate-200 bg-white text-slate-600 hover:border-indigo-300"
                    )}
                  >
                    {loc}
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-slate-400">
              Pick one or more. Used to default your job-search location.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="visa">Visa status</Label>
            <Input
              id="visa"
              value={p.visa_status ?? ""}
              onChange={(e) => set({ visa_status: e.target.value || null })}
              placeholder="e.g. Australian citizen / Student visa (subclass 500)"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="links">Links (label: url, one per line)</Label>
            <Textarea
              id="links"
              rows={2}
              value={Object.entries(p.links)
                .map(([k, v]) => `${k}: ${v}`)
                .join("\n")}
              onChange={(e) => {
                const links: Record<string, string> = {};
                for (const line of e.target.value.split("\n")) {
                  const idx = line.indexOf(":");
                  if (idx > 0) {
                    links[line.slice(0, idx).trim()] = line
                      .slice(idx + 1)
                      .trim();
                  }
                }
                set({ links });
              }}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Skills</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          {(["technical", "tools", "soft"] as const).map((key) => (
            <div key={key} className="space-y-1.5">
              <Label htmlFor={`skills-${key}`} className="capitalize">
                {key} (comma-separated)
              </Label>
              <Textarea
                id={`skills-${key}`}
                rows={3}
                value={toComma(p.skills[key])}
                onChange={(e) =>
                  set({ skills: { ...p.skills, [key]: fromComma(e.target.value) } })
                }
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>Education</CardTitle>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              set({
                education: [
                  ...p.education,
                  { institution: null, degree: null, field: null, start_date: null, end_date: null, grade: null },
                ],
              })
            }
          >
            <Plus className="h-4 w-4" /> Add
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {p.education.map((edu, i) => (
            <div key={i} className="grid gap-2 rounded-md border p-3 md:grid-cols-3">
              <Input placeholder="Institution" value={edu.institution ?? ""} onChange={(e) => { const education = [...p.education]; education[i] = { ...edu, institution: e.target.value || null }; set({ education }); }} />
              <Input placeholder="Degree" value={edu.degree ?? ""} onChange={(e) => { const education = [...p.education]; education[i] = { ...edu, degree: e.target.value || null }; set({ education }); }} />
              <Input placeholder="Field" value={edu.field ?? ""} onChange={(e) => { const education = [...p.education]; education[i] = { ...edu, field: e.target.value || null }; set({ education }); }} />
              <Input placeholder="Start (e.g. 2023)" value={edu.start_date ?? ""} onChange={(e) => { const education = [...p.education]; education[i] = { ...edu, start_date: e.target.value || null }; set({ education }); }} />
              <Input placeholder="End (e.g. 2026)" value={edu.end_date ?? ""} onChange={(e) => { const education = [...p.education]; education[i] = { ...edu, end_date: e.target.value || null }; set({ education }); }} />
              <div className="flex gap-2">
                <Input placeholder="Grade / GPA" value={edu.grade ?? ""} onChange={(e) => { const education = [...p.education]; education[i] = { ...edu, grade: e.target.value || null }; set({ education }); }} />
                <Button type="button" variant="ghost" size="icon" aria-label="Remove education entry" onClick={() => set({ education: p.education.filter((_, j) => j !== i) })}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>Experience</CardTitle>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              set({
                experience: [
                  ...p.experience,
                  { title: null, company: null, location: null, start_date: null, end_date: null, bullets: [] },
                ],
              })
            }
          >
            <Plus className="h-4 w-4" /> Add
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {p.experience.map((exp, i) => (
            <div key={i} className="space-y-2 rounded-md border p-3">
              <div className="grid gap-2 md:grid-cols-4">
                <Input placeholder="Title" value={exp.title ?? ""} onChange={(e) => { const experience = [...p.experience]; experience[i] = { ...exp, title: e.target.value || null }; set({ experience }); }} />
                <Input placeholder="Company" value={exp.company ?? ""} onChange={(e) => { const experience = [...p.experience]; experience[i] = { ...exp, company: e.target.value || null }; set({ experience }); }} />
                <Input placeholder="Start" value={exp.start_date ?? ""} onChange={(e) => { const experience = [...p.experience]; experience[i] = { ...exp, start_date: e.target.value || null }; set({ experience }); }} />
                <div className="flex gap-2">
                  <Input placeholder="End" value={exp.end_date ?? ""} onChange={(e) => { const experience = [...p.experience]; experience[i] = { ...exp, end_date: e.target.value || null }; set({ experience }); }} />
                  <Button type="button" variant="ghost" size="icon" aria-label="Remove experience entry" onClick={() => set({ experience: p.experience.filter((_, j) => j !== i) })}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <Textarea placeholder="Bullets — one per line" rows={3} value={toLines(exp.bullets)} onChange={(e) => { const experience = [...p.experience]; experience[i] = { ...exp, bullets: fromLines(e.target.value) }; set({ experience }); }} />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>Projects</CardTitle>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              set({
                projects: [
                  ...p.projects,
                  { name: null, description: null, tech: [], outcomes: [] },
                ],
              })
            }
          >
            <Plus className="h-4 w-4" /> Add
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {p.projects.map((proj, i) => (
            <div key={i} className="space-y-2 rounded-md border p-3">
              <div className="flex gap-2">
                <Input placeholder="Project name" value={proj.name ?? ""} onChange={(e) => { const projects = [...p.projects]; projects[i] = { ...proj, name: e.target.value || null }; set({ projects }); }} />
                <Button type="button" variant="ghost" size="icon" aria-label="Remove project" onClick={() => set({ projects: p.projects.filter((_, j) => j !== i) })}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
              <Textarea placeholder="Description" rows={2} value={proj.description ?? ""} onChange={(e) => { const projects = [...p.projects]; projects[i] = { ...proj, description: e.target.value || null }; set({ projects }); }} />
              <Input placeholder="Tech (comma-separated)" value={toComma(proj.tech)} onChange={(e) => { const projects = [...p.projects]; projects[i] = { ...proj, tech: fromComma(e.target.value) }; set({ projects }); }} />
              <Textarea placeholder="Outcomes — one per line" rows={2} value={toLines(proj.outcomes)} onChange={(e) => { const projects = [...p.projects]; projects[i] = { ...proj, outcomes: fromLines(e.target.value) }; set({ projects }); }} />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Certifications</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="One per line: name | issuer | year"
            rows={2}
            value={p.certifications
              .map((c) => [c.name, c.issuer, c.year].filter(Boolean).join(" | "))
              .join("\n")}
            onChange={(e) =>
              set({
                certifications: fromLines(e.target.value).map((line) => {
                  const [name, issuer, year] = line.split("|").map((s) => s.trim());
                  return { name: name || null, issuer: issuer || null, year: year || null };
                }),
              })
            }
          />
        </CardContent>
      </Card>

      <Button type="submit" disabled={saving}>
        {saving ? "Saving…" : "Save profile"}
      </Button>
    </form>
  );
}
