import logging
import pandas as pd
from datetime import datetime
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit
from .account_generation import generate_account_for_user

User = get_user_model()
logger = logging.getLogger(__name__)

ALLOWED_ROLES = {
    "EMPLOYEE": UserRole.EMPLOYEE,
    "BU_MANAGER": UserRole.BU_MANAGER,
    "TRAINER_TUTOR": UserRole.TRAINER_TUTOR,
    "INTERN": UserRole.INTERN,
    "CLIENT": UserRole.CLIENT,
    
    # French aliases
    "COLLABORATEUR": UserRole.EMPLOYEE,
    "MANAGER": UserRole.BU_MANAGER,
    "FORMATEUR": UserRole.TRAINER_TUTOR,
    "TUTEUR": UserRole.TRAINER_TUTOR,
    "STAGIAIRE": UserRole.INTERN,
}

def parse_date(date_str):
    if pd.isna(date_str) or not date_str:
        return None
    try:
        return pd.to_datetime(date_str).date()
    except Exception:
        return None

def parse_and_validate_file(file_obj, filename: str) -> dict:
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file_obj, dtype=str)
        elif filename.endswith(".xlsx"):
            df = pd.read_excel(file_obj, dtype=str)
        else:
            return {"error": "Format de fichier non supporté. Seuls .csv et .xlsx sont acceptés."}
    except Exception as e:
        logger.error(f"Error parsing file {filename}: {e}")
        return {"error": "Le fichier est corrompu ou illisible."}

    # Normalize columns
    original_columns = list(df.columns)
    col_map = {}
    for c in original_columns:
        norm = str(c).strip().lower()
        if "prénom" in norm or "first" in norm: col_map[c] = "first_name"
        elif "nom" in norm or "last" in norm: col_map[c] = "last_name"
        elif "email" in norm or "mail" in norm: col_map[c] = "email"
        elif "phone" in norm or "tel" in norm or "tél" in norm: col_map[c] = "phone"
        elif "profil" in norm or "role" in norm or "rôle" in norm: col_map[c] = "role"
        elif "bu" in norm or "business" in norm: col_map[c] = "bu"
        elif "poste" in norm or "position" in norm: col_map[c] = "position"
        elif "supervis" in norm: col_map[c] = "supervisor"
        elif "école" in norm or "ecole" in norm or "school" in norm: col_map[c] = "school"
        elif "spécial" in norm or "special" in norm: col_map[c] = "specialization"
        elif "type" in norm and "stage" in norm: col_map[c] = "internship_type"
        elif "début" in norm or "start" in norm: col_map[c] = "internship_start"
        elif "fin" in norm or "end" in norm: col_map[c] = "internship_end"
        elif "rémunér" in norm or "paid" in norm: col_map[c] = "paid"
        elif "sujet" in norm or "subject" in norm: col_map[c] = "subject_title"
        else: col_map[c] = norm

    df.rename(columns=col_map, inplace=True)

    def get_str(row_series, key):
        val = row_series.get(key)
        if pd.isna(val) or val is None:
            return ""
        return str(val).strip()

    valid_rows = []
    invalid_rows = []
    skipped_rows = []
    
    seen_emails = set()

    for index, row in df.iterrows():
        row_num = index + 2 # +1 for 0-index, +1 for header
        errors = []
        
        email = get_str(row, "email")
        if not email:
            errors.append("Email est requis.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Format d'email invalide.")
                
        if email in seen_emails:
            errors.append("Email dupliqué dans le fichier.")
        else:
            if email:
                seen_emails.add(email)
                
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
            
        bu_code = get_str(row, "bu")
        bu_obj = None
        if bu_code and role != UserRole.CLIENT:
            bu_obj = BusinessUnit.objects.filter(code__iexact=bu_code).first()
            if not bu_obj:
                bu_obj = BusinessUnit.objects.filter(name__iexact=bu_code).first()
            if not bu_obj:
                errors.append(f"Business Unit introuvable: {bu_code}")
        elif role in [UserRole.EMPLOYEE, UserRole.BU_MANAGER, UserRole.TRAINER_TUTOR, UserRole.INTERN] and not bu_code:
            errors.append("Business Unit est requise pour ce profil.")

        supervisor_email = get_str(row, "supervisor")
        supervisor_obj = None
        if supervisor_email:
            supervisor_obj = User.objects.filter(email=supervisor_email).first()
            if not supervisor_obj:
                errors.append(f"Superviseur introuvable: {supervisor_email}")

        start_date = parse_date(row.get("internship_start"))
        end_date = parse_date(row.get("internship_end"))
        
        if role == UserRole.INTERN:
            if start_date and end_date and start_date > end_date:
                errors.append("La date de début de stage doit être avant la date de fin.")

        if errors:
            invalid_rows.append({
                "row": row_num,
                "data": {k: (v if pd.notna(v) else None) for k, v in row.to_dict().items()},
                "errors": errors
            })
        else:
            paid_str = get_str(row, "paid").lower()
            paid = paid_str in ["oui", "yes", "true", "1"]
            
            valid_rows.append({
                "row": row_num,
                "payload": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "contact_email": email,
                    "phone_number": get_str(row, "phone"),
                    "role": role,
                    "business_unit": bu_obj.id if bu_obj else None,
                    "position": get_str(row, "position"),
                    "supervisor": supervisor_obj.id if supervisor_obj else None,
                    "school": get_str(row, "school"),
                    "specialization": get_str(row, "specialization"),
                    "internship_type": get_str(row, "internship_type"),
                    "paid": paid,
                    "internship_start": start_date.isoformat() if start_date else None,
                    "internship_end": end_date.isoformat() if end_date else None,
                    "subject_title": get_str(row, "subject_title"),
                }
            })

    return {
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "skipped_count": len(skipped_rows),
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "skipped_rows": skipped_rows
    }


def execute_import(valid_rows: list, actor) -> list:
    """
    Executes the import for the valid rows.
    Returns a list of results with generated credentials.
    Note: The calling view should wrap this in an atomic transaction if desired, 
    but `generate_account_for_user` uses its own atomic block for each user.
    To ensure all-or-nothing, the view MUST wrap the call to `execute_import` in transaction.atomic().
    """
    results = []
    
    for row_data in valid_rows:
        payload = row_data["payload"]
        
        # Hydrate related objects
        if payload.get("business_unit"):
            payload["business_unit"] = BusinessUnit.objects.get(id=payload["business_unit"])
        if payload.get("supervisor"):
            payload["supervisor"] = User.objects.get(id=payload["supervisor"])
            
        gen_result = generate_account_for_user(payload, actor=actor)
        
        results.append({
            "first_name": payload["first_name"],
            "last_name": payload["last_name"],
            "contact_email": payload["contact_email"],
            "professional_email": gen_result["email"],
            "temporary_password": gen_result["temporary_password"],
            "status": "Créé" if gen_result["is_new"] else "Mis à jour"
        })
        
    return results
