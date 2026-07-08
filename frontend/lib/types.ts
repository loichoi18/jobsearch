/** Mirrors backend/ingestion/profile_schema.py — keep in sync. */

export interface EducationEntry {
  institution: string | null;
  degree: string | null;
  field: string | null;
  start_date: string | null;
  end_date: string | null;
  grade: string | null;
}

export interface ExperienceEntry {
  title: string | null;
  company: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  bullets: string[];
}

export interface ProjectEntry {
  name: string | null;
  description: string | null;
  tech: string[];
  outcomes: string[];
}

export interface Skills {
  technical: string[];
  tools: string[];
  soft: string[];
}

export interface CertificationEntry {
  name: string | null;
  issuer: string | null;
  year: string | null;
}

export interface Profile {
  name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  preferred_locations: string[];
  education: EducationEntry[];
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  skills: Skills;
  certifications: CertificationEntry[];
  visa_status: string | null;
  links: Record<string, string>;
}

export const emptyProfile: Profile = {
  name: null,
  email: null,
  phone: null,
  location: null,
  preferred_locations: [],
  education: [],
  experience: [],
  projects: [],
  skills: { technical: [], tools: [], soft: [] },
  certifications: [],
  visa_status: null,
  links: {},
};

/** Mirrors backend/services/jobs_schemas.py — keep in sync. */

export type JobStatus =
  | "saved"
  | "applied"
  | "interview"
  | "offer"
  | "rejected";

export const JOB_STATUSES: JobStatus[] = [
  "saved",
  "applied",
  "interview",
  "offer",
  "rejected",
];

export interface JobSearchResult {
  adzuna_id: string;
  title: string;
  company: string | null;
  location: string | null;
  salary_min: number | null;
  salary_max: number | null;
  snippet: string | null;
  redirect_url: string | null;
}

export interface JobSearchResponse {
  results: JobSearchResult[];
  count: number | null;
  page: number;
}

/** Mirrors backend/services/matching_schemas.py — keep in sync. */

export type SkillImportance = "required" | "preferred";

export interface MissingSkill {
  name: string;
  importance: SkillImportance;
  evidence: string;
}

export interface CriterionBreakdown {
  technical_skills: number;
  experience_relevance: number;
  education_fit: number;
  nice_to_haves: number;
}

export interface MatchAnalysis {
  match_score: number;
  semantic_score: number;
  rubric_score: number;
  breakdown: CriterionBreakdown;
  matched_skills: string[];
  missing_skills: MissingSkill[];
  one_line_verdict: string;
  short_description: boolean;
}

/** Mirrors backend/generation/doc_schemas.py — keep in sync. */

export type DocType = "cv" | "cover_letter";
export type DocumentStatus = "pending" | "complete" | "failed";

export interface DraftUnit {
  text: string;
  chunk_ids: string[];
}

export interface DraftSection {
  title: string;
  units: DraftUnit[];
}

export interface DraftDocument {
  doc_type: DocType;
  sections: DraftSection[];
}

export interface ClaimVerdict {
  claim: string;
  chunk_ids: string[];
  verdict: "grounded" | "unsupported";
  note: string | null;
}

export interface GroundingReport {
  claims: ClaimVerdict[];
  grounding_rate: number;
  removed_claims: string[];
}

export interface DocumentRow {
  id: string;
  doc_type: DocType;
  version: number;
  status: DocumentStatus;
  typst_source?: string | null;
  pdf_path?: string | null;
  grounding_report: GroundingReport | null;
  error?: string | null;
  created_at: string | null;
}

export interface Job {
  id: string;
  source: "adzuna" | "manual";
  title: string;
  company: string | null;
  location: string | null;
  description: string | null;
  url: string | null;
  salary_min: number | null;
  salary_max: number | null;
  status: JobStatus;
  match_score: number | null;
  skill_gaps: MatchAnalysis | null;
  applied_at: string | null;
  updated_at: string | null;
  created_at: string | null;
}

/** Mirrors backend/services/insights_schemas.py — keep in sync. */

export interface GapEvidence {
  job_id: string;
  job_title: string;
  company: string | null;
  importance: string;
  phrase: string;
}

export interface SkillGapInsight {
  skill: string;
  frequency: number;
  pct_of_jobs: number;
  required_count: number;
  preferred_count: number;
  impact: number;
  evidence: GapEvidence[];
}

export interface SkillGapsResponse {
  jobs_analyzed: number;
  gaps: SkillGapInsight[];
}

export interface UpskillItem {
  skill: string;
  why_it_matters: string;
  learning_path: string;
  project_idea: string;
}

export interface UpskillPlan {
  items: UpskillItem[];
}

/** Mirrors backend/evaluation/schemas.py — keep in sync. */

export interface EvalCaseResult {
  case_id: string;
  title: string;
  doc_type: string;
  grounding_rate: number;
  fabrication_rate: number;
  keyword_coverage: number;
  leaked_claims: string[];
  missing_keywords: string[];
  pages: number | null;
  length_compliant: boolean;
  latency_s: number;
  est_tokens: number;
  est_cost_usd: number;
  error: string | null;
}

export interface EvalAggregate {
  cases: number;
  grounding_rate: number;
  fabrication_rate: number;
  keyword_coverage: number;
  length_compliance: number;
  avg_latency_s: number;
  total_est_tokens: number;
  total_est_cost_usd: number;
  errors: number;
}

export interface EvalRunReport {
  dataset_version: string;
  mock: boolean;
  created_at: string;
  aggregate: EvalAggregate;
  cases: EvalCaseResult[];
}

/** A row from the eval_runs table. */
export interface EvalRun {
  id: string;
  dataset_version: string;
  created_at: string;
  metrics: EvalRunReport;
}
