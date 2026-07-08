/** Preset AU locations for the profile multi-select and job-search default. */
export const AU_LOCATIONS: string[] = [
  "Sydney, NSW",
  "Melbourne, VIC",
  "Brisbane, QLD",
  "Perth, WA",
  "Adelaide, SA",
  "Canberra, ACT",
  "Gold Coast, QLD",
  "Newcastle, NSW",
  "Wollongong, NSW",
  "Hobart, TAS",
  "Darwin, NT",
  "Remote (Australia)",
];

/** The city portion of a "City, STATE" label — what Adzuna's `where` expects. */
export function cityOf(location: string): string {
  return location.split(",")[0].trim();
}
