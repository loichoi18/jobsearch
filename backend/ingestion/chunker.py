"""Semantic profile chunking: each project, role, and education entry becomes
its own chunk; skills are grouped by category. Target 100-300 tokens/chunk
(short entries are fine — they are semantically complete units)."""

from pydantic import BaseModel, Field

from ingestion.profile_schema import Profile


class ProfileChunk(BaseModel):
    section: str
    title: str
    content: str
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def build(cls, section: str, title: str, content: str) -> "ProfileChunk":
        return cls(
            section=section,
            title=title,
            content=content.strip(),
            metadata={"section": section, "title": title},
        )


def _join(parts: list[str | None]) -> str:
    return " | ".join(p for p in parts if p)


def chunk_profile(profile: Profile) -> list[ProfileChunk]:
    chunks: list[ProfileChunk] = []

    for edu in profile.education:
        title = _join([edu.degree, edu.institution]) or "Education"
        lines = [
            _join([edu.degree, edu.field]),
            f"Institution: {edu.institution}" if edu.institution else None,
            _join([edu.start_date, edu.end_date]),
            f"Grade: {edu.grade}" if edu.grade else None,
        ]
        content = "\n".join(line for line in lines if line)
        if content:
            chunks.append(ProfileChunk.build("education", title, content))

    for exp in profile.experience:
        title = _join([exp.title, exp.company]) or "Experience"
        header = _join(
            [exp.title, exp.company, exp.location, _join([exp.start_date, exp.end_date])]
        )
        content = "\n".join([header, *[f"- {b}" for b in exp.bullets]])
        if content.strip():
            chunks.append(ProfileChunk.build("experience", title, content))

    for proj in profile.projects:
        title = proj.name or "Project"
        lines = [
            proj.name,
            proj.description,
            f"Tech: {', '.join(proj.tech)}" if proj.tech else None,
            *[f"Outcome: {o}" for o in proj.outcomes],
        ]
        content = "\n".join(line for line in lines if line)
        if content:
            chunks.append(ProfileChunk.build("project", title, content))

    skills = profile.skills
    for category, items in (
        ("technical", skills.technical),
        ("tools", skills.tools),
        ("soft", skills.soft),
    ):
        if items:
            chunks.append(
                ProfileChunk.build(
                    "skills",
                    f"{category.capitalize()} skills",
                    f"{category.capitalize()} skills: {', '.join(items)}",
                )
            )

    if profile.certifications:
        lines = [
            _join([c.name, c.issuer, c.year]) for c in profile.certifications
        ]
        chunks.append(
            ProfileChunk.build(
                "certifications", "Certifications", "\n".join(lines)
            )
        )

    basics: list[str] = []
    if profile.visa_status:
        basics.append(f"Visa / work rights: {profile.visa_status}")
    if profile.links:
        basics.extend(f"{label}: {url}" for label, url in profile.links.items())
    if basics:
        chunks.append(ProfileChunk.build("basics", "Basics", "\n".join(basics)))

    return chunks
