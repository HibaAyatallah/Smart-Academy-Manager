"""Deterministic, section-aware chunking for structured CV content."""

from dataclasses import dataclass
import hashlib
import re


@dataclass(frozen=True)
class CVChunk:
    section: str
    chunk_index: int
    text: str
    content_hash: str


def _normalize(text: str) -> str:
    return re.sub(r"[ \t]+", " ", str(text or "")).strip()


def chunk_text(text: str, *, size: int, overlap: int) -> list[str]:
    if size < 100:
        raise ValueError("La taille de chunk doit être au moins égale à 100 caractères.")
    if overlap < 0 or overlap >= size:
        raise ValueError("L’overlap doit être positif ou nul et inférieur à la taille du chunk.")
    text = _normalize(text)
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + max(1, size // 2), end + 1)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        next_start = max(0, end - overlap)
        if next_start > 0:
            boundary = text.find(" ", next_start, end)
            if boundary != -1:
                next_start = boundary + 1
        start = next_start if next_start > start else end
    return chunks


def chunk_sections(sections: list[tuple[str, str]], *, size: int, overlap: int) -> list[CVChunk]:
    result = []
    seen = set()
    for section, text in sections:
        for value in chunk_text(text, size=size, overlap=overlap):
            normalized_key = value.casefold()
            if normalized_key in seen:
                continue
            seen.add(normalized_key)
            index = sum(item.section == section for item in result)
            result.append(CVChunk(
                section=section,
                chunk_index=index,
                text=value,
                content_hash=hashlib.sha256(value.encode("utf-8")).hexdigest(),
            ))
    return result


def cv_sections(analysis) -> list[tuple[str, str]]:
    sections = []
    profile = " ".join(value for value in [analysis.full_name, analysis.location] if value)
    sections.append(("PROFILE", profile))
    sections.append(("SKILLS", ", ".join(analysis.skills)))
    experiences = "\n".join(
        " | ".join(str(item.get(key, "")).strip() for key in (
            "position", "company", "start_date", "end_date", "description"
        ) if str(item.get(key, "")).strip())
        for item in analysis.experiences
    )
    sections.append(("EXPERIENCE", experiences))
    education = "\n".join(
        " | ".join(str(item.get(key, "")).strip() for key in (
            "title", "institution", "start_date", "end_date"
        ) if str(item.get(key, "")).strip())
        for item in analysis.education
    )
    if analysis.diplomas:
        education = "\n".join(filter(None, [education, ", ".join(analysis.diplomas)]))
    sections.append(("EDUCATION", education))
    sections.append(("LANGUAGES", ", ".join(analysis.languages)))
    sections.append(("CERTIFICATIONS", ", ".join(analysis.certifications)))
    sections.append(("POSITIONS", ", ".join(analysis.positions)))
    sections.append(("COMPANIES", ", ".join(analysis.companies)))
    if analysis.raw_text:
        sections.append(("RAW_TEXT", analysis.raw_text))
    return [(section, text) for section, text in sections if _normalize(text)]
