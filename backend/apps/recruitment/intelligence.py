import hashlib
import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from django.db import transaction

from .choices import ApplicationDocumentType
from .models import Application, ApplicationMatch, CVAnalysis, Offer, TrainingRecommendation

EXTRACTOR_VERSION = "structured-v6"
SECTION_NAMES = {
    "skills": ("compétences", "competences", "skills", "technologies", "technical skills", "compétences techniques", "compétences professionnelles", "competences professionnelles", "compétences personnelles", "competences personnelles", "professional skills", "soft skills"),
    "experience": ("expériences", "experiences", "expérience", "experience", "expérience professionnelle", "expérience professionel", "experience professionel", "expériences professionnelles", "work experience", "professional experience", "employment", "parcours professionnel"),
    "education": ("formations", "formation", "éducation", "education", "diplômes", "diplomes", "academic background", "parcours académique", "parcours academique", "études", "etudes"),
    "languages": ("langues", "languages"),
    "certifications": ("certifications", "certificats", "certificates"),
    "interests": ("centres d’intérêt", "centres d'interet", "centres dinteret", "intérêts", "interets", "loisirs", "interests", "hobbies"),
    "availability": ("disponibilités", "disponibilites", "disponibilité", "disponibilite", "conditions de travail", "préférences de travail", "preferences de travail", "work preferences", "availability"),
    "projects": ("projets", "projet", "projets académiques", "projets academiques", "projects", "academic projects"),
    "profile": ("profil", "profile", "à propos", "a propos", "about me", "summary"),
    "engagements": ("engagements", "vie associative", "volunteering", "bénévolat", "benevolat"),
    "contact": ("contact", "coordonnées", "coordonnees", "contact details"),
    "references": ("références", "references"),
}
DATE_RANGE = re.compile(
    r"(?P<start>(?:0?[1-9]|1[0-2])[/.-]\d{4}|\d{4})\s*(?:[-–—à]|to)\s*"
    r"(?P<end>(?:0?[1-9]|1[0-2])[/.-]\d{4}|\d{4}|présent|present|actuel|current)", re.I
)
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_CANDIDATE = re.compile(
    r"(?<!\d)(?:(?:\+|00)?212[\s.()/-]*[67](?:[\s.()/-]*\d){8}|0[67](?:[\s.()/-]*\d){8})(?!\d)"
)
MONTH_DATE_RANGE = re.compile(
    r"(?P<start>(?:janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+\d{4}|\d{4})"
    r"\s*(?:[-–—à]|to)\s*(?P<end>(?:janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+\d{4}|\d{4}|présent|present|actuel|current)", re.I
)
MONTH_ONLY_RANGE = re.compile(
    r"(?P<start>janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)"
    r"\s*(?:[-–—à]|to)\s*(?P<end>(?:janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+\d{4}|présent|present)", re.I
)

INSTITUTION_PATTERN = re.compile(
    r"\b(?:universit[ée]|university|[ée]cole|school|institut|institute|facult[ée]|academy|"
    r"groupe\s+scolaire|emsi|encg|ensa|ensam|est|fst|ofppt|ista|iscae|uir|um6p|hassan\s+ii)\b",
    re.I,
)
DEGREE_PATTERN = re.compile(
    r"\b(?:bac(?:calaur[ée]at)?|licence|bachelor|master|dipl[oô]me|doctorat|ph\.?d|"
    r"cycle\s+(?:d['’]\s*)?ing[ée]nierie|cycle\s+ing[ée]nieur|ing[ée]nieur|technicien|deug|dut|bts|"
    r"cycle\s+pr[ée]paratoire|\d(?:re|ère|e|ème)?\s+ann[ée]e)\b",
    re.I,
)
JOB_PATTERN = re.compile(
    r"\b(?:vendeu(?:r|se)|d[ée]veloppeu(?:r|se)|developer|engineer|ing[ée]nieur(?:e)?|consultant(?:e)?|"
    r"stagiaire|manager|responsable|assistant(?:e)?|comptable|commercial(?:e)?|"
    r"technicien(?:ne)?|analyste|designer|chef\s+de\s+projet|serveu(?:r|se)|"
    r"caissi(?:er|[èe]re)|enseignant(?:e)?|formateur|administrat(?:eur|rice))\b",
    re.I,
)
COMPANY_PATTERN = re.compile(
    r"\b(?:sarl|sa|sas|ltd|llc|inc|groupe|group|company|soci[ée]t[ée]|entreprise|cabinet)\b",
    re.I,
)
CITY_PATTERN = re.compile(
    r"\b(?:casablanca|rabat|marrakech|tanger|f[èe]s|agadir|mekn[èe]s|k[ée]nitra|"
    r"t[ée]touan|oujda|el\s+jadida|safi|mohammedia|maroc|morocco)\b",
    re.I,
)
LANGUAGE_PATTERN = re.compile(
    r"^(?:fran[çc]ais|french|anglais|english|arabe|arabic|espagnol|spanish|allemand|german|"
    r"italien|italian|amazigh|tamazight)(?:\s*[:\-–—]\s*.+)?$",
    re.I,
)
WORK_CONDITION_PATTERN = re.compile(
    r"^(?:week[ -]?end|présentiel|presentiel|télétravail|teletravail|hybride|remote|"
    r"horaires? décalés?|travail (?:le soir|de nuit)|soir|nuit|temps plein|temps partiel|"
    r"disponible|disponibilité|mobilité|immediate|immédiate)$",
    re.I,
)
TECH_SKILL_PATTERN = re.compile(
    r"\b(?:python|django|flask|fastapi|java|spring|javascript|typescript|angular|react(?:\.js)?|"
    r"vue(?:\.js)?|node(?:\.js)?|php|laravel|symfony|c\+\+|c#|\.net|sql|postgresql|mysql|"
    r"mongodb|docker|kubernetes|git|linux|aws|azure|gcp|power\s*bi|excel)\b",
    re.I,
)


class CVExtractionError(ValueError):
    pass


@dataclass
class ExtractedDocument:
    text: str
    method: str
    warnings: list[str]


def _extract_pdf(file_bytes: bytes) -> ExtractedDocument:
    import pymupdf

    try:
        with pymupdf.open(stream=file_bytes, filetype="pdf") as document:
            text = "\n".join(_ordered_pdf_page_text(page) for page in document)
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise CVExtractionError("Le CV PDF est invalide ou corrompu.") from exc

    if not re.sub(r"\s+", "", text):
        raise CVExtractionError(
            "Ce PDF ne contient pas de texte exploitable. "
            "Veuillez utiliser un PDF textuel ou un fichier DOCX."
        )
    return ExtractedDocument(text, "PDF_TEXT", [])


def _ordered_pdf_page_text(page) -> str:
    """Rebuild a stable reading order from positioned text blocks.

    PyMuPDF's plain-text order follows the PDF content stream, which can
    alternate unrelated columns. When both page halves contain several
    blocks, read each column top-to-bottom; otherwise preserve visual order.
    """
    blocks = [block for block in page.get_text("blocks") if block[6] == 0 and block[4].strip()]
    if not blocks:
        return ""
    starts = sorted(set(block[0] for block in blocks))
    gaps = [(right - left, left, right) for left, right in zip(starts, starts[1:])]
    largest_gap = max(gaps, default=(0, 0, 0))
    if largest_gap[0] >= page.rect.width * 0.12:
        split = (largest_gap[1] + largest_gap[2]) / 2
        left = [block for block in blocks if block[0] < split]
        right = [block for block in blocks if block[0] >= split]
    else:
        left, right = [], []
    if len(left) >= 3 and len(right) >= 3:
        ordered = sorted(left, key=lambda block: (block[1], block[0])) + sorted(
            right, key=lambda block: (block[1], block[0])
        )
    else:
        ordered = sorted(blocks, key=lambda block: (round(block[1] / 4), block[0]))
    return "\n".join(block[4].strip() for block in ordered)


def _extract_docx(file_bytes: bytes) -> ExtractedDocument:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document = Document(BytesIO(file_bytes))
    except Exception as exc:
        raise CVExtractionError("Le CV DOCX est invalide ou corrompu.") from exc
    parts = []
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            value = Paragraph(child, document).text.strip()
            if value:
                parts.append(value)
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            for row in table.rows:
                for cell in row.cells:
                    parts.extend(value.strip() for value in cell.text.splitlines() if value.strip())
    return ExtractedDocument("\n".join(parts), "DOCX", [])


def extract_document(uploaded_file, filename: str | None = None) -> tuple[ExtractedDocument, bytes]:
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    suffix = Path(filename or getattr(uploaded_file, "name", "")).suffix.lower()
    if suffix == ".pdf":
        result = _extract_pdf(raw)
    elif suffix == ".docx":
        result = _extract_docx(raw)
    elif suffix == ".txt":  # retained for deterministic unit tests only
        result = ExtractedDocument(raw.decode("utf-8", errors="ignore"), "TEXT", [])
    else:
        raise CVExtractionError("Format de CV non pris en charge. Utilisez PDF ou DOCX.")
    if not result.text.strip():
        raise CVExtractionError("Le CV ne contient aucun texte exploitable.")
    return result, raw


def _repair_character_spaced_line(line: str) -> str:
    """Repair PDFs whose embedded font maps emit one token per character.

    Original word boundaries are represented by repeated spaces, while letters
    inside a word have one space. Normal lines are returned unchanged.
    """
    stripped = line.strip()
    tokens = stripped.split()
    if len(tokens) < 4:
        return stripped
    single = sum(len(token) == 1 for token in tokens)
    if single / len(tokens) < 0.68:
        return stripped
    words = []
    for group in re.split(r"\s{2,}", stripped):
        compact = re.sub(r"(?<=\S)\s(?=\S)", "", group)
        if compact:
            words.append(compact)
    return " ".join(words)


def normalize_extracted_text(text: str) -> str:
    repaired = "\n".join(_repair_character_spaced_line(line) for line in text.splitlines())
    # Multi-column PDFs sometimes concatenate the next uppercase heading to
    # the final value of the preceding section.
    return re.sub(r"(?<=[a-zà-ÿé])(?=[A-ZÉÈÀÙÇ]{5,}(?:\s|$))", "\n", repaired)


def _clean_lines(text: str) -> list[str]:
    text = normalize_extracted_text(text)
    lines = []
    for line in text.splitlines():
        line = re.sub(r"(?:\s*\|\s*){2,}", " ", line)
        line = re.sub(r"\s+", " ", line).strip(" •·|\t")
        if line:
            lines.append(line)
    return lines


def _normalized_heading(line: str) -> str:
    return re.sub(r"[^a-zà-ÿ ]", "", line.casefold()).strip()


def _heading_match(line: str) -> tuple[str, str]:
    """Return a section and optional inline value for an explicit heading."""
    stripped = line.strip()
    before, separator, after = stripped.partition(":")
    candidate = _normalized_heading(before if separator else stripped)
    for name, labels in SECTION_NAMES.items():
        if candidate in {_normalized_heading(label) for label in labels}:
            return name, after.strip() if separator else ""
    return "", ""


def detect_sections(lines: list[str]) -> dict[str, list[str]]:
    """Assign lines to sections without interpreting their field structure."""
    values = {name: [] for name in SECTION_NAMES}
    current = ""
    semantic_education = False
    for line in lines:
        found, remainder = _heading_match(line)
        if found:
            current = found
            semantic_education = False
            if remainder:
                values[current].append(remainder)
            continue

        if LANGUAGE_PATTERN.fullmatch(line.strip(" •")):
            values["languages"].append(line)
            semantic_education = False
            continue
        education_signal = bool(
            DEGREE_PATTERN.search(line)
            and current in {"", "education", "experience"}
            and len(line) <= 120
            and not re.search(r"\b(?:je|i am|i'm|étudiant(?:e)?|student)\b", line, re.I)
        )
        education_continuation = semantic_education and bool(
            INSTITUTION_PATTERN.search(line)
            or _date_match(line)
            or (line.isupper() and len(line.split()) <= 8)
        )
        if education_signal or education_continuation:
            values["education"].append(line)
            semantic_education = True
            continue
        semantic_education = False
        if current:
            values[current].append(line)
    return values


def _unique(values):
    result = []
    seen = set()
    for value in values:
        value = re.sub(r"(?:\s*\|\s*)+", " ", value).strip(" ,;•·-")
        value = re.sub(r"\s+", " ", value)
        key = _fold(value)
        if value and key not in seen:
            seen.add(key); result.append(value)
    return result


def _split_items(lines: list[str]) -> list[str]:
    return _unique(item for line in lines for item in re.split(r"[,;|•·]", line) if 1 < len(item.strip()) < 100)


def _skill_items(lines: list[str]) -> list[str]:
    values = []
    for line in lines:
        # Category labels such as "Frameworks:" describe the following values;
        # they are not themselves candidate skills.
        content = line.split(":", 1)[1] if ":" in line else line
        values.extend(re.split(r"[,;|•·]", content))
    return _unique(
        value for value in values
        if 1 < len(value.strip()) < 80
        and not WORK_CONDITION_PATTERN.fullmatch(value.strip())
        and not INSTITUTION_PATTERN.search(value)
        and not DEGREE_PATTERN.search(value)
        and not _heading_match(value)[0]
    )


def _normalize_skills(skills: list[str]) -> list[str]:
    folded = {_fold(skill): skill for skill in skills}
    if "react" in folded and "native" in folded:
        skills = [skill for skill in skills if _fold(skill) not in {"react", "native"}]
        skills.append("React Native")
    return _unique(skills)


def _fold(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(char))


def _heading_kind(line: str) -> str:
    return _heading_match(line)[0]


def _section_indexes(lines: list[str]) -> dict[int, str]:
    result: dict[int, str] = {}
    current = ""
    for index, line in enumerate(lines):
        found = _heading_kind(line)
        if found:
            current = found; result[index] = "heading"
        elif current:
            result[index] = current
    return result


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("00212"):
        digits = digits[2:]
    if re.fullmatch(r"212[67]\d{8}", digits):
        return f"+{digits}"
    if re.fullmatch(r"0[67]\d{8}", digits):
        return f"+212{digits[1:]}"
    return ""


def _extract_phones(lines: list[str]) -> list[str]:
    return _unique(
        normalized for line in lines for match in PHONE_CANDIDATE.finditer(line)
        if (normalized := _normalize_phone(match.group(0)))
    )


def _plausible_name_line(line: str) -> bool:
    words = line.strip().split()
    if not 1 <= len(words) <= 5 or not 2 <= len(line) <= 80:
        return False
    if any(char.isdigit() for char in line) or EMAIL.search(line) or PHONE_CANDIDATE.search(line):
        return False
    if not all(re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+", word) for word in words):
        return False
    if JOB_PATTERN.search(line) or INSTITUTION_PATTERN.search(line) or DEGREE_PATTERN.search(line):
        return False
    if COMPANY_PATTERN.search(line) or CITY_PATTERN.fullmatch(line.strip()):
        return False
    return _fold(line) not in {
        "curriculum vitae", "cv", "profil", "profile", "contact", "competences", "skills",
        "experience", "experiences", "formation", "formations", "education", "langues",
        "languages", "certifications", "loisirs", "interets", "centres dinteret",
        "disponibilites", "conditions de travail", "references",
    }


def _name_score(index: int, line: str, lines: list[str], contact_indexes: set[int]) -> int:
    if not _plausible_name_line(line):
        return -100
    score = max(0, 34 - index * 3)
    if 2 <= len(line.split()) <= 4:
        score += 22
    if line.isupper() or line.istitle():
        score += 8
    distance = min((abs(index - contact) for contact in contact_indexes), default=99)
    if distance <= 2:
        score += 24 - distance * 5
    email_parts = {
        _fold(part) for email_line in lines for email in EMAIL.findall(email_line)
        for part in re.split(r"[._+-]", email.split("@", 1)[0]) if len(part) > 1
    }
    score += 8 * sum(_fold(word) in email_parts for word in line.split())
    email_locals = [_fold(email.split("@", 1)[0]) for email_line in lines for email in EMAIL.findall(email_line)]
    score += 12 * sum(any(_fold(word) in local for local in email_locals) for word in line.split())
    previous = lines[index - 1] if index else ""
    following = lines[index + 1] if index + 1 < len(lines) else ""
    if JOB_PATTERN.search(previous) or DATE_RANGE.search(following):
        score -= 45
    if INSTITUTION_PATTERN.search(previous) or INSTITUTION_PATTERN.search(following):
        score -= 30
    return score


def _detect_name(lines: list[str], section_indexes: dict[int, str]) -> tuple[str, int]:
    contact_indexes = {index for index, line in enumerate(lines) if EMAIL.search(line) or PHONE_CANDIDATE.search(line)}
    candidates: list[tuple[int, str, int]] = []
    for index, line in enumerate(lines[:60]):
        near_contact = any(abs(index - contact) <= 2 for contact in contact_indexes)
        email_related = any(
            _fold(word) in _fold(email.split("@", 1)[0])
            for word in line.split()
            for email_line in lines
            for email in EMAIL.findall(email_line)
            if len(word) > 2
        )
        # Multi-column extraction can place the visual header after a section.
        # In that case proximity to a validated contact may override section order.
        if (section_indexes.get(index) and not near_contact and not email_related) or re.search(r"https?://|linkedin|curriculum|vitae", line, re.I):
            continue
        score = _name_score(index, line, lines, contact_indexes)
        if score >= 35:
            candidates.append((score, line, index))
        if (
            len(line.split()) == 1
            and index + 1 < min(len(lines), 60)
            and (not section_indexes.get(index + 1) or near_contact)
            and len(lines[index + 1].split()) == 1
            and _plausible_name_line(line)
            and _plausible_name_line(lines[index + 1])
            and not _heading_kind(line)
            and not _heading_kind(lines[index + 1])
        ):
            combined = f"{line} {lines[index + 1]}"
            pair_score = _name_score(index, combined, lines, contact_indexes) + 10
            if pair_score >= 35:
                candidates.append((pair_score, combined, index))
    if not candidates:
        return "", 0
    score, value, _ = max(candidates, key=lambda item: (item[0], -item[2]))
    return value, min(100, score)


def _city_from_line(line: str) -> str:
    matches = list(CITY_PATTERN.finditer(line))
    if not matches:
        return ""
    return next((match.group(0) for match in matches if _fold(match.group(0)) not in {"maroc", "morocco"}), matches[0].group(0))


def _detect_location(lines: list[str]) -> tuple[str, int]:
    for line in lines[:25]:
        match = re.match(r"(?:adresse|address|localisation|location|ville|city)\s*[:|-]\s*(.+)", line, re.I)
        if match:
            value = match.group(1).strip()
            if not INSTITUTION_PATTERN.search(value) and not COMPANY_PATTERN.search(value):
                return value, 95
            city = _city_from_line(value)
            return (city, 65) if city else ("", 0)
    for line in lines[:25]:
        city = _city_from_line(line)
        if not city:
            continue
        if INSTITUTION_PATTERN.search(line) or COMPANY_PATTERN.search(line):
            return city, 55
        if len(line.split()) <= 5:
            return line.strip(), 75
    return "", 0


def _institution_and_city(value: str) -> tuple[str, str]:
    city = _city_from_line(value)
    institution = value
    if city:
        institution = re.sub(rf"\s*[-–—|,]\s*{re.escape(city)}(?:\s*[-–—|,]\s*(?:Maroc|Morocco))?\s*$", "", institution, flags=re.I)
    return institution.strip(" -–—|,"), city


def _validate_parsed_data(data: dict) -> dict:
    name = data.get("full_name", "").strip()
    conflicts = {_fold(value) for value in [*data.get("companies", []), *data.get("positions", [])] if value}
    if not _plausible_name_line(name) or _fold(name) in conflicts:
        name = ""
    data["full_name"] = name
    data["first_name"] = name.split()[0] if name else ""
    data["last_name"] = " ".join(name.split()[1:]) if name else ""
    data["phone"] = _normalize_phone(data.get("phone", ""))
    data["contact_details"]["phones"] = [data["phone"]] if data["phone"] else []
    location = data.get("location", "").strip()
    if INSTITUTION_PATTERN.search(location) or COMPANY_PATTERN.search(location):
        location = _city_from_line(location)
    data["location"] = location
    data["contact_details"]["location"] = location
    return data


def _date_match(value: str):
    return DATE_RANGE.search(value) or MONTH_DATE_RANGE.search(value) or MONTH_ONLY_RANGE.search(value)


def _without_date(value: str) -> str:
    value = DATE_RANGE.sub("", value)
    value = MONTH_DATE_RANGE.sub("", value)
    value = MONTH_ONLY_RANGE.sub("", value)
    return re.sub(r"(?:\s*\|\s*){2,}", " ", value).strip(" -–—|,")


def _experience_records(lines: list[str]) -> list[dict]:
    records = []
    pending: list[str] = []
    groups: list[list[str]] = []
    for line in lines:
        cleaned = re.sub(r"(?:\s*\|\s*){2,}", " ", line).strip(" |")
        if not cleaned:
            continue
        pending.append(cleaned)
        if _date_match(cleaned):
            groups.append(pending); pending = []
        elif len(pending) >= 3 and JOB_PATTERN.search(pending[-1]) and JOB_PATTERN.search(pending[0]):
            groups.append(pending[:-1]); pending = [pending[-1]]
    if pending:
        groups.append(pending)

    for group in groups:
        date_line = next((line for line in group if _date_match(line)), "")
        date = _date_match(date_line) if date_line else None
        content = [_without_date(line) for line in group if _without_date(line)]
        if not content:
            continue
        chunks = [part.strip() for part in re.split(r"\s+\|\s+|\s+@\s+", " | ".join(content)) if part.strip()]
        position_index = next((i for i, value in enumerate(chunks) if JOB_PATTERN.search(value)), None)
        position = chunks[position_index] if position_index is not None else ""
        company = ""
        if position:
            combined = [part.strip() for part in re.split(r"\s+[-–—]\s+", position, maxsplit=1)]
            if len(combined) == 2 and JOB_PATTERN.search(combined[0]):
                position, company = combined
            if not company:
                company = next(
                    (
                        value for i, value in enumerate(chunks)
                        if i != position_index
                        and not CITY_PATTERN.fullmatch(value.strip())
                        and not DEGREE_PATTERN.search(value)
                        and not INSTITUTION_PATTERN.search(value)
                    ),
                    "",
                )
        description = "\n".join(_unique(content))
        record = {
            "position": position, "company": company,
            "start_date": date.group("start") if date else "",
            "end_date": date.group("end") if date else "",
            "duration": date_line.strip(" |") if date else "",
            "description": description,
        }
        records.append(record)
    merged = []
    for record in records:
        if merged and not record["start_date"] and not record["end_date"]:
            previous = merged[-1]
            previous["description"] = "\n".join(
                _unique([previous["description"], record["description"]])
            )
            if not previous["position"] and record["position"]:
                previous["position"] = record["position"]
            if not previous["company"] and record["company"]:
                previous["company"] = record["company"]
        else:
            merged.append(record)
    result, seen = [], set()
    for record in merged:
        if record["position"] or record["company"]:
            key = tuple(_fold(record[field]) for field in ("position", "company", "start_date", "end_date"))
        else:
            key = tuple(_fold(record[field]) for field in ("start_date", "end_date", "description"))
        if key not in seen:
            seen.add(key); result.append(record)
    return result


def _education_records(lines: list[str]) -> list[dict]:
    records = []
    current = None
    for line in lines:
        if EMAIL.search(line) or PHONE_CANDIDATE.search(line):
            continue
        date = _date_match(line)
        cleaned = _without_date(line)
        if not cleaned and date:
            if current and not current["institution"] and not current["start_date"] and not current["end_date"]:
                current["start_date"], current["end_date"] = date.group("start"), date.group("end")
            continue
        parts = [part.strip() for part in re.split(r"\s+\|\s+|\s+@\s+", cleaned) if part.strip()]
        for part in parts:
            if INSTITUTION_PATTERN.search(part):
                institution, _ = _institution_and_city(part)
                if current and not current["institution"]:
                    current["institution"] = institution
                else:
                    current = {"title": "", "institution": institution, "start_date": "", "end_date": ""}
                    records.append(current)
            elif DEGREE_PATTERN.search(part):
                if current and not current["title"]:
                    current["title"] = part
                else:
                    current = {"title": part, "institution": "", "start_date": "", "end_date": ""}
                    records.append(current)
            elif current and not current["title"]:
                current["title"] = part
            elif current and not current["institution"] and part.isupper() and len(part.split()) <= 8:
                current["title"] = f'{current["title"]} {part}'.strip()
            if date and current:
                if not current["start_date"] and not current["end_date"]:
                    current["start_date"], current["end_date"] = date.group("start"), date.group("end")
    return _unique_records(records, ("title", "institution", "start_date", "end_date"))


def _unique_records(records: list[dict], fields: tuple[str, ...]) -> list[dict]:
    result, seen = [], set()
    for record in records:
        key = tuple(_fold(str(record.get(field, ""))) for field in fields)
        if any(key) and key not in seen:
            seen.add(key); result.append(record)
    return result


def parse_cv_text(text: str) -> dict:
    lines = _clean_lines(text)
    normalized_text = "\n".join(lines)
    sections = detect_sections(lines)
    section_indexes = _section_indexes(lines)
    emails = _unique(EMAIL.findall(normalized_text))
    phones = _extract_phones(lines)
    name, name_confidence = _detect_name(lines, section_indexes)
    location, location_confidence = _detect_location(lines)

    experiences = _experience_records(sections["experience"])
    companies = _unique(item["company"] for item in experiences if item["company"])
    positions = _unique(item["position"] for item in experiences if item["position"])
    education = _education_records(sections["education"])
    certifications = _split_items(sections["certifications"])
    languages = _unique(
        item for item in _split_items(sections["languages"])
        if LANGUAGE_PATTERN.fullmatch(item.strip())
    )
    skills = _normalize_skills(
        [item for item in _skill_items(sections["skills"]) if not DATE_RANGE.search(item)]
    )
    if not skills:
        # Without an explicit section, only accept a conservative technology
        # vocabulary; never promote arbitrary neighbouring labels to skills.
        skills = _normalize_skills(
            sorted(_unique(match.group(0).casefold() for match in TECH_SKILL_PATTERN.finditer(normalized_text)))
        )
    data = {
        "first_name": name.split()[0] if name else "",
        "last_name": " ".join(name.split()[1:]) if name else "",
        "full_name": name,
        "email": emails[0] if emails else "",
        "phone": phones[0] if phones else "",
        "location": location,
        "skills": skills,
        "experiences": experiences,
        "education": education,
        "diplomas": [item["title"] for item in education if item["title"]],
        "companies": _unique(companies),
        "positions": _unique(positions),
        "languages": languages,
        "certifications": certifications,
        "contact_details": {
            "emails": emails, "phones": phones, "location": location,
            "confidence": {"name": name_confidence, "email": 100 if emails else 0,
                           "phone": 100 if phones else 0, "location": location_confidence},
        },
    }
    return _validate_parsed_data(data)


def extract_cv_data(uploaded_file, filename: str | None = None) -> dict:
    document, raw = extract_document(uploaded_file, filename)
    data = parse_cv_text(document.text)
    data.update({"source_sha256": hashlib.sha256(raw).hexdigest(), "extraction_method": document.method, "extraction_warnings": document.warnings, "extractor_version": EXTRACTOR_VERSION})
    return data


def extract_cv(application: Application, *, force=False) -> CVAnalysis:
    document = application.documents.filter(document_type=ApplicationDocumentType.CV).order_by("-uploaded_at").first()
    if not document:
        raise CVExtractionError("Aucun CV n’est associé à cette candidature.")
    with document.file.open("rb") as source:
        data = extract_cv_data(source, document.original_name or document.file.name)
    data.pop("first_name", None)
    data.pop("last_name", None)
    existing = getattr(application, "cv_analysis", None)
    if existing and existing.human_validated and not force:
        raise CVExtractionError("Les données ont déjà été corrigées et validées. Confirmez la réanalyse.")
    defaults = {**data, "human_validated": False, "validated_by": None, "validated_at": None}
    analysis, _ = CVAnalysis.objects.update_or_create(application=application, defaults=defaults)
    return analysis


@transaction.atomic
def match_application(application: Application) -> list[ApplicationMatch]:
    analysis = getattr(application, "cv_analysis", None) or extract_cv(application)
    candidate_skills = {skill.casefold() for skill in analysis.skills}
    results = []
    offers = Offer.objects.exclude(required_skills="")
    if application.offer_id:
        offers = offers.filter(pk=application.offer_id)
    for offer in offers:
        required = {item.strip().casefold() for item in re.split(r"[,;\n]", offer.required_skills) if item.strip()}
        matched, missing = sorted(required & candidate_skills), sorted(required - candidate_skills)
        score = round(100 * len(matched) / len(required), 2) if required else 0
        item, _ = ApplicationMatch.objects.update_or_create(application=application, offer=offer, defaults={"score": score, "matched_skills": matched, "missing_skills": missing, "explanation": f"{len(matched)} compétence(s) correspondante(s) sur {len(required)} requise(s).", "human_decision": "PENDING", "reviewed_by": None, "reviewed_at": None})
        results.append(item)
    missing_all = {skill for item in results for skill in item.missing_skills}
    from apps.trainings.models import Training
    for training in Training.objects.all():
        searchable = f"{training.title} {training.description} {training.category} {training.objectives}".casefold()
        covered = sorted(skill for skill in missing_all if skill in searchable)
        if covered:
            TrainingRecommendation.objects.update_or_create(application=application, training=training, defaults={"score": round(100 * len(covered) / len(missing_all), 2), "skill_gaps": covered, "explanation": f"Cette formation couvre {len(covered)} écart(s) de compétences détecté(s).", "human_decision": "PENDING"})
    return results
