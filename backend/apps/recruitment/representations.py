"""Stable text representations and fingerprints for hybrid matching inputs.

This module deliberately contains no embedding provider. It defines the boundary
that a future local embedding implementation will consume.
"""

import hashlib
import json


REPRESENTATION_VERSION = "matching-text-v2"


def _clean(value) -> str:
    return " ".join(str(value or "").split())


def _lines(title: str, values) -> list[str]:
    cleaned = [_clean(value) for value in values if _clean(value)]
    return [f"{title}: {', '.join(cleaned)}"] if cleaned else []


def build_candidate_representation(application, analysis) -> str:
    """Return deterministic, human-readable candidate text for embeddings."""
    sections = [f"representation_version: {REPRESENTATION_VERSION}"]
    sections += _lines("skills", analysis.skills)
    sections += _lines("positions", analysis.positions)
    sections += _lines("companies", analysis.companies)
    sections += _lines("diplomas", analysis.diplomas)
    sections += _lines("languages", analysis.languages)
    sections += _lines("certifications", analysis.certifications)
    sections += _lines("profile_study_level", [application.candidate_profile.study_level])
    for item in analysis.experiences:
        text = " | ".join(
            part for part in (
                _clean(item.get("position")), _clean(item.get("company")),
                _clean(item.get("start_date")), _clean(item.get("end_date")),
                _clean(item.get("description")),
            ) if part
        )
        if text:
            sections.append(f"experience: {text}")
    for item in analysis.education:
        text = " | ".join(
            part for part in (
                _clean(item.get("title")), _clean(item.get("institution")),
                _clean(item.get("start_date")), _clean(item.get("end_date")),
            ) if part
        )
        if text:
            sections.append(f"education: {text}")
    # Keep the complete extracted CV as a semantic source. The structured
    # parser is intentionally conservative and may not classify projects,
    # missions or uncommon technologies, while bge-m3 can still compare them
    # directly with the offer. Normalizing whitespace keeps cache keys stable.
    raw_text = _clean(analysis.raw_text)
    if raw_text:
        sections.append(f"cv_full_text: {raw_text}")
    return "\n".join(sections)


def build_offer_representation(offer) -> str:
    """Return deterministic offer text for direct candidate/offer embeddings."""
    sections = [
        f"representation_version: {REPRESENTATION_VERSION}",
        f"title: {_clean(offer.title)}",
        f"description_and_missions: {_clean(offer.description)}",
    ]
    sections += _lines("required_skills", [offer.required_skills])
    sections += _lines("required_level", [offer.required_level])
    sections += _lines("required_experience_years", [offer.required_experience_years])
    sections += _lines("application_type", [offer.application_type])
    sections += _lines("location", [offer.location])
    return "\n".join(section for section in sections if not section.endswith(": "))


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def data_fingerprint(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def candidate_matching_fingerprint(application, analysis) -> str:
    return data_fingerprint({
        "representation": build_candidate_representation(application, analysis),
        "extractor_version": analysis.extractor_version,
    })


def offer_matching_fingerprint(offer) -> str:
    return data_fingerprint({"representation": build_offer_representation(offer)})
