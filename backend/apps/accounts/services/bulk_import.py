import logging
import unicodedata
import pandas as pd
from django.contrib.auth import get_user_model
from django.db import transaction
from types import SimpleNamespace
from apps.business_units.services import assign_business_unit, current_business_unit
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
from apps.business_units.choices import ALLOWED_BUSINESS_UNITS
from apps.recruitment.models import InternProfile
from .account_generation import generate_account_for_user

User = get_user_model()
logger = logging.getLogger(__name__)

ALLOWED_ROLES = {
    "EMPLOYEE": UserRole.EMPLOYEE,
    "BU_MANAGER": UserRole.BU_MANAGER,
    "TRAINER_TUTOR": UserRole.TRAINER_TUTOR,
    "INTERN": UserRole.INTERN,
    "CLIENT": UserRole.CLIENT,
    "CLIENT_EXTERNE": UserRole.CLIENT,
    
    # French aliases
    "COLLABORATEUR": UserRole.EMPLOYEE,
    "MANAGER": UserRole.BU_MANAGER,
    "FORMATEUR": UserRole.TRAINER_TUTOR,
    "TUTEUR": UserRole.TRAINER_TUTOR,
    "STAGIAIRE": UserRole.INTERN,
}

EMPTY_MARKERS = {"", "nan", "nat", "none", "null"}


def _flatten_cell_values(value):
    if isinstance(value, pd.Series):
        values = value.tolist()
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]
    cleaned = []
    for item in values:
        if item is None:
            continue
        try:
            if bool(pd.isna(item)):
                continue
        except (TypeError, ValueError):
            pass
        text = str(item).strip()
        if text.lower() not in EMPTY_MARKERS:
            cleaned.append(text)
    return cleaned


def _coalesce_cell_values(value):
    distinct = list(dict.fromkeys(_flatten_cell_values(value)))
    return (distinct[0] if len(distinct) == 1 else ""), distinct


def clean_value(val):
    value, conflicts = _coalesce_cell_values(val)
    if not value and not conflicts:
        return None
    if len(conflicts) > 1:
        return conflicts
    if hasattr(val, "isoformat") and not isinstance(val, (pd.Series, list, tuple, set)):
        return val.isoformat()
    return value

def parse_date(date_str):
    date_str, conflicts = _coalesce_cell_values(date_str)
    if len(conflicts) > 1 or not date_str:
        return None
    try:
        # Handles both float Excel dates and standard string dates if parsed as objects
        return pd.to_datetime(date_str).date()
    except Exception:
        return None

def parse_and_validate_file(file_obj, filename: str) -> dict:
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file_obj, dtype=str)
        elif filename.endswith(".xlsx"):
            try:
                df = pd.read_excel(file_obj, sheet_name="Donnees_a_importer", dtype=str)
            except ValueError:
                file_obj.seek(0)
                df = pd.read_excel(file_obj, dtype=str)
        else:
            return {"error": "Format de fichier non supporté. Seuls .csv et .xlsx sont acceptés."}
    except Exception as exc:
        logger.error("Bulk import file parsing failed error_type=%s", exc.__class__.__name__)
        return {"error": "Le fichier est corrompu ou illisible."}

    # Normalize and consolidate aliases without producing duplicate labels.
    original_columns = list(df.columns)

    def normalize_header(column):
        raw = str(column).strip().lower().replace("-", "_").replace(" ", "_")
        norm = "".join(
            char for char in unicodedata.normalize("NFKD", raw)
            if not unicodedata.combining(char)
        )
        exact = {
            "import_id": "import_id", "prenom": "first_name", "nom": "last_name",
            "email_personnel_contact": "email", "telephone": "phone",
            "role_plateforme": "role", "business_unit": "bu", "bu": "bu",
            "poste_fonction": "position", "encadrant_reference": "supervisor",
            "ecole": "school", "specialite": "specialization",
            "date_debut_stage": "internship_start", "date_fin_stage": "internship_end",
            "type_profil": "type_profil",
        }
        if norm in exact:
            return exact[norm]
        if "prenom" in norm or "first" in norm: return "first_name"
        if norm == "nom" or "last" in norm: return "last_name"
        if "email" in norm or "mail" in norm: return "email"
        if "phone" in norm or "tel" in norm: return "phone"
        if "profil" in norm or "role" in norm: return "role"
        if norm.startswith("bu_") or norm.endswith("_bu") or "business" in norm: return "bu"
        if "poste" in norm or "position" in norm: return "position"
        if "supervis" in norm: return "supervisor"
        if "ecole" in norm or "school" in norm: return "school"
        if "special" in norm: return "specialization"
        if "type" in norm and "stage" in norm: return "internship_type"
        if "debut" in norm or "start" in norm: return "internship_start"
        if "fin" in norm or "end" in norm: return "internship_end"
        if "remuner" in norm or "paid" in norm: return "paid"
        if "sujet" in norm or "subject" in norm: return "subject_title"
        return norm

    groups = {}
    for position, original in enumerate(original_columns):
        groups.setdefault(normalize_header(original), []).append((position, str(original)))

    normalized_data = {}
    for canonical, sources in groups.items():
        if len(sources) == 1:
            normalized_data[canonical] = df.iloc[:, sources[0][0]]
            continue
        merged = []
        for row_index in range(len(df.index)):
            values = [df.iloc[row_index, position] for position, _ in sources]
            value, distinct = _coalesce_cell_values(values)
            if len(distinct) > 1:
                source_names = ", ".join(name for _, name in sources)
                return {
                    "error": (
                        f"Colonnes contradictoires pour « {canonical} » à la ligne {row_index + 2} "
                        f"({source_names}) : {', '.join(distinct)}."
                    )
                }
            merged.append(value or None)
        normalized_data[canonical] = pd.Series(merged, index=df.index)
    df = pd.DataFrame(normalized_data, index=df.index)

    cell_conflicts = []

    def get_str(row_series, key):
        value, conflicts = _coalesce_cell_values(row_series.get(key))
        if len(conflicts) > 1:
            cell_conflicts.append(f"{key}: {', '.join(conflicts)}")
            return ""
        return value

    valid_rows = []
    invalid_rows = []
    skipped_rows = []
    
    seen_emails = set()
    seen_import_ids = set()
    missing_bus = set()
    
    # Pre-scan for supervisors (emails and full names) in the file
    file_supervisors = set()
    for _, row in df.iterrows():
        em = get_str(row, "email").lower()
        if em:
            file_supervisors.add(em)
        fn = get_str(row, "first_name").strip().lower()
        ln = get_str(row, "last_name").strip().lower()
        if fn and ln:
            file_supervisors.add(f"{fn} {ln}")

    for row_num, row in df.iterrows():
        # Excel rows are usually 1-indexed and header is row 1
        row_num += 2 
        
        errors = []
        warnings = []
        email = get_str(row, "email")
        if email and email in seen_emails:
            errors.append("Email dupliqué dans le fichier.")
        else:
            if email:
                seen_emails.add(email)

        import_id = get_str(row, "import_id")
        if import_id and import_id in seen_import_ids:
            errors.append("Import_ID dupliqué dans le fichier.")
        else:
            if import_id:
                seen_import_ids.add(import_id)
        
        if not email:
            errors.append("Email est requis.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Format d'email invalide.")
                
        if email and User.objects.filter(contact_email=email).exists():
            skipped_rows.append({
                "row": row_num,
                "email": email,
                "reason": "Un utilisateur avec cet email personnel existe déjà."
            })
            continue

        first_name = get_str(row, "first_name")
        last_name = get_str(row, "last_name")
        
        if not first_name: errors.append("Prénom est requis.")
        if not last_name: errors.append("Nom est requis.")

        role_str = get_str(row, "role").upper()
        role = ALLOWED_ROLES.get(role_str)
        if not role:
            errors.append(f"Rôle ou profil invalide: {role_str}")
            
        bu_code = get_str(row, "bu").strip()
        bu_obj = None
        if bu_code and role != UserRole.CLIENT:
            # Normalize: trim + case-insensitive search
            bu_obj = BusinessUnit.objects.filter(code__iexact=bu_code).first()
            if not bu_obj:
                bu_obj = BusinessUnit.objects.filter(name__iexact=bu_code).first()
            if not bu_obj:
                missing_bus.add(bu_code)
                allowed = ", ".join(ALLOWED_BUSINESS_UNITS.keys())
                errors.append(
                    f"Ligne {row_num} ({email or 'email manquant'}) — "
                    f"Business Unit inconnue : « {bu_code} ». "
                    f"Valeurs autorisées : {allowed}."
                )
        elif role in [UserRole.EMPLOYEE, UserRole.BU_MANAGER, UserRole.TRAINER_TUTOR, UserRole.INTERN] and not bu_code:
            errors.append("Business Unit est requise pour ce profil (COLLABORATEUR, MANAGER, FORMATEUR, STAGIAIRE).")

        supervisor_email = get_str(row, "supervisor")
        supervisor_obj = None
        if supervisor_email:
            from django.db.models import Value
            from django.db.models.functions import Concat
            
            supervisor_obj = User.objects.filter(contact_email__iexact=supervisor_email).first()
            if not supervisor_obj:
                supervisor_obj = User.objects.filter(email__iexact=supervisor_email).first()
            if not supervisor_obj:
                supervisor_obj = User.objects.annotate(
                    full_name=Concat('first_name', Value(' '), 'last_name')
                ).filter(full_name__iexact=supervisor_email.strip()).first()
                
            if not supervisor_obj:
                if supervisor_email.lower().strip() in file_supervisors:
                    warnings.append(f"Encadrant créé pendant cet import : {supervisor_email}")
                else:
                    warnings.append(f"Superviseur introuvable, il sera ignoré : {supervisor_email}")

        start_date = parse_date(row.get("internship_start"))
        end_date = parse_date(row.get("internship_end"))
        
        if role == UserRole.INTERN:
            if start_date and end_date and start_date > end_date:
                errors.append("La date de début de stage doit être avant la date de fin.")

        if errors:
            invalid_rows.append({
                "row": row_num,
                "data": {str(k).strip(): clean_value(v) for k, v in row.to_dict().items()},
                "errors": errors
            })
        else:
            paid_str = get_str(row, "paid").lower()
            paid = paid_str in ["oui", "yes", "true", "1"]
            
            valid_rows.append({
                "row": row_num,
                "warnings": warnings,
                "payload": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "contact_email": email,
                    "phone_number": get_str(row, "phone"),
                    "role": role,
                    # Store None for CLIENT (no BU needed) or when BU found by ID
                    "business_unit": bu_obj.id if bu_obj else (None if role == UserRole.CLIENT else bu_code),
                    "business_unit_name": bu_obj.name if bu_obj else (None if role == UserRole.CLIENT else bu_code),
                    "position": get_str(row, "position"),
                    "supervisor": supervisor_obj.id if supervisor_obj else supervisor_email,
                    "school": get_str(row, "school"),
                    "specialization": get_str(row, "specialization"),
                    "internship_type": get_str(row, "internship_type"),
                    "paid": paid,
                    "internship_start": start_date.isoformat() if start_date else None,
                    "internship_end": end_date.isoformat() if end_date else None,
                    "subject_title": get_str(row, "subject_title"),
                }
            })

    if cell_conflicts:
        return {"error": "Valeurs contradictoires détectées : " + "; ".join(cell_conflicts)}

    return {
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "skipped_count": len(skipped_rows),
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "skipped_rows": skipped_rows,
        "missing_bus": list(missing_bus)
    }


@transaction.atomic
def execute_import(valid_rows: list, actor) -> list:
    """
    Executes the import for the valid rows using a multi-pass strategy.
    To ensure all-or-nothing, the view MUST wrap the call to `execute_import` in transaction.atomic().
    """
    results = []
    import uuid
    import_id = str(uuid.uuid4())
    
    user_mapping = {}
    row_results = {}
    previous_units = {}
    audit_request = SimpleNamespace(user=actor, method="POST", path="/api/import/confirm/")
    
    # Pass 1: User Base Accounts Creation
    for row_data in valid_rows:
        payload = dict(row_data["payload"]) # copy
        row_num = row_data["row"]
        
        # Bypass relations for now
        payload["business_unit"] = None
        payload["supervisor"] = None
        payload["_defer_business_unit_assignment"] = True
        
        existing = User.objects.filter(contact_email=payload["contact_email"]).first() or User.objects.filter(email=payload["contact_email"]).first()
        previous_units[row_num] = current_business_unit(existing) if existing else None
        gen_result = generate_account_for_user(payload, actor=actor)
        user_obj = gen_result["user"]
        
        # Track for later passes
        user_mapping[payload["contact_email"]] = user_obj
        
        row_results[row_num] = {
            "ID d'import": import_id,
            "Nom Complet": f"{payload['first_name']} {payload['last_name']}".strip(),
            "Rôle": payload["role"],
            "Business Unit": "", # updated later
            "Email Professionnel": gen_result["email"],
            "Mot de passe temporaire": gen_result["temporary_password"] or "********",
            "Statut": "Créé" if gen_result["is_new"] else "Mis à jour",
            "Erreur": ""
        }
        
    # Pass 2: verify all BU references are resolved (must be integer IDs at this point).
    # Imports never create Business Units — they must reference the centrally managed
    # catalogue (NetSEC, System, Software, Achat) which is seeded via migration.
    for row_data in valid_rows:
        payload = row_data["payload"]
        bu_val = payload.get("business_unit")
        if isinstance(bu_val, str):
            email = payload.get("contact_email", "inconnu")
            allowed = ", ".join(ALLOWED_BUSINESS_UNITS.keys())
            raise ValueError(
                f"Business Unit non résolue pour {email} : « {bu_val} ». "
                f"Valeurs autorisées : {allowed}. "
                "Vérifiez que les quatre BU officielles existent en base "
                "(lancez : python manage.py migrate)."
            )
                
    # Pass 3: Profile & BU Membership Assignment
    for row_data in valid_rows:
        payload = row_data["payload"]
        user_obj = user_mapping[payload["contact_email"]]
        role = payload["role"]
        
        bu_val = payload.get("business_unit")
        bu_obj = None
        if isinstance(bu_val, str):
            bu_obj = bu_mapping.get(bu_val)
        elif bu_val:
            bu_obj = BusinessUnit.objects.get(id=bu_val)
            
        if bu_obj:
            row_results[row_data["row"]]["Business Unit"] = bu_obj.name
            
        assign_business_unit(user_obj, getattr(bu_obj, "pk", None), request=audit_request, previous=previous_units[row_data["row"]])
        if bu_obj and role != UserRole.BU_MANAGER:
            BusinessUnitMembership.objects.filter(user=user_obj, business_unit=bu_obj, is_active=True).update(position=payload.get("position", ""))

    # Pass 4: Supervisor Resolution
    for row_data in valid_rows:
        payload = row_data["payload"]
        role = payload["role"]
        
        if role == UserRole.INTERN:
            supervisor_val = payload.get("supervisor")
            supervisor_obj = None
            
            if isinstance(supervisor_val, int):
                supervisor_obj = User.objects.filter(id=supervisor_val).first()
            elif isinstance(supervisor_val, str):
                from django.db.models import Value
                from django.db.models.functions import Concat
                
                # We can also check user_mapping from the current import
                for contact_email, u in user_mapping.items():
                    if u.contact_email.lower() == supervisor_val.lower() or u.email.lower() == supervisor_val.lower():
                        supervisor_obj = u
                        break
                    full_name = f"{u.first_name} {u.last_name}".lower()
                    if full_name == supervisor_val.lower().strip():
                        supervisor_obj = u
                        break
                
                if not supervisor_obj:
                    # check DB
                    supervisor_obj = User.objects.filter(contact_email__iexact=supervisor_val).first()
                    if not supervisor_obj:
                        supervisor_obj = User.objects.filter(email__iexact=supervisor_val).first()
                    if not supervisor_obj:
                        supervisor_obj = User.objects.annotate(
                            full_name=Concat('first_name', Value(' '), 'last_name')
                        ).filter(full_name__iexact=supervisor_val.strip()).first()
                        
            if supervisor_obj:
                user_obj = user_mapping[payload["contact_email"]]
                profile = InternProfile.objects.get(user=user_obj)
                assign_business_unit(
                    user_obj,
                    profile.business_unit_id,
                    supervisor=supervisor_obj,
                    previous=profile.business_unit,
                )
                
    for row_num in sorted(row_results.keys()):
        results.append(row_results[row_num])
        
    return results
