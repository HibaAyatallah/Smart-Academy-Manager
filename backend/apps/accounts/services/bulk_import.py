import logging
import pandas as pd
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnit, BusinessUnitMembership
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
    
    # French aliases
    "COLLABORATEUR": UserRole.EMPLOYEE,
    "MANAGER": UserRole.BU_MANAGER,
    "FORMATEUR": UserRole.TRAINER_TUTOR,
    "TUTEUR": UserRole.TRAINER_TUTOR,
    "STAGIAIRE": UserRole.INTERN,
}

def clean_value(val):
    if pd.isna(val) or val is None or str(val).strip().lower() in ["nan", "nat", "none", ""]:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val).strip()

def parse_date(date_str):
    if pd.isna(date_str) or not date_str or str(date_str).strip().lower() in ["nan", "nat", "none", ""]:
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
    except Exception as e:
        logger.error(f"Error parsing file {filename}: {e}")
        return {"error": f"Le fichier est corrompu ou illisible. {str(e)}"}

    # Normalize columns
    original_columns = list(df.columns)
    col_map = {}
    for c in original_columns:
        norm = str(c).strip().lower()
        if norm == "import_id": col_map[c] = "import_id"
        elif norm == "prenom": col_map[c] = "first_name"
        elif norm == "nom": col_map[c] = "last_name"
        elif norm == "email_personnel_contact": col_map[c] = "email"
        elif norm == "telephone": col_map[c] = "phone"
        elif norm == "role_plateforme": col_map[c] = "role"
        elif norm == "business_unit": col_map[c] = "bu"
        elif norm == "poste_fonction": col_map[c] = "position"
        elif norm == "encadrant_reference": col_map[c] = "supervisor"
        elif norm == "ecole": col_map[c] = "school"
        elif norm == "specialite": col_map[c] = "specialization"
        elif norm == "date_debut_stage": col_map[c] = "internship_start"
        elif norm == "date_fin_stage": col_map[c] = "internship_end"
        elif norm == "type_profil": col_map[c] = "type_profil" # avoid fuzzy matching "profil" to "role"
        
        # Fuzzy fallback for tests
        elif "prénom" in norm or "first" in norm: col_map[c] = "first_name"
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
            
        bu_code = get_str(row, "bu")
        bu_obj = None
        if bu_code and role != UserRole.CLIENT:
            bu_obj = BusinessUnit.objects.filter(code__iexact=bu_code).first()
            if not bu_obj:
                bu_obj = BusinessUnit.objects.filter(name__iexact=bu_code).first()
            if not bu_obj:
                missing_bus.add(bu_code)
                warnings.append(f"Business Unit manquante et sera créée : {bu_code}")
        elif role in [UserRole.EMPLOYEE, UserRole.BU_MANAGER, UserRole.TRAINER_TUTOR, UserRole.INTERN] and not bu_code:
            errors.append("Business Unit est requise pour ce profil.")

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
                    "business_unit": bu_obj.id if bu_obj else bu_code,
                    "business_unit_name": bu_obj.name if bu_obj else bu_code,
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

    return {
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "skipped_count": len(skipped_rows),
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "skipped_rows": skipped_rows,
        "missing_bus": list(missing_bus)
    }


def execute_import(valid_rows: list, actor, create_missing_bus=False) -> list:
    """
    Executes the import for the valid rows using a multi-pass strategy.
    To ensure all-or-nothing, the view MUST wrap the call to `execute_import` in transaction.atomic().
    """
    results = []
    import uuid
    import_id = str(uuid.uuid4())
    
    user_mapping = {}
    row_results = {}
    
    # Pass 1: User Base Accounts Creation
    for row_data in valid_rows:
        payload = dict(row_data["payload"]) # copy
        row_num = row_data["row"]
        
        # Bypass relations for now
        payload["business_unit"] = None
        payload["supervisor"] = None
        
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
        
    # Pass 2: Create Missing Business Units & Assign Managers
    bu_mapping = {}
    if create_missing_bus:
        missing_bu_names = set()
        for row_data in valid_rows:
            bu_val = row_data["payload"].get("business_unit")
            if isinstance(bu_val, str):
                missing_bu_names.add(bu_val)
                
        fallback_manager = User.objects.filter(role=UserRole.BU_MANAGER).first()
        
        for bu_name in missing_bu_names:
            manager = None
            # Find a BU_MANAGER for this BU from the current import batch
            for row_data in valid_rows:
                if row_data["payload"].get("role") == UserRole.BU_MANAGER and row_data["payload"].get("business_unit") == bu_name:
                    manager = user_mapping[row_data["payload"]["contact_email"]]
                    break
                    
            if not manager:
                manager = fallback_manager
                
            if manager:
                bu_obj, _ = BusinessUnit.objects.get_or_create(
                    name=bu_name,
                    defaults={
                        "code": bu_name.strip().upper().replace(" ", "_"),
                        "manager": manager
                    }
                )
                bu_mapping[bu_name] = bu_obj
            else:
                raise ValueError(f"Impossible de créer la Business Unit '{bu_name}': Aucun BU_MANAGER disponible.")
                
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
            
            if role == UserRole.INTERN:
                InternProfile.objects.filter(user=user_obj).update(business_unit=bu_obj)
                
            if role != UserRole.CLIENT:
                BusinessUnitMembership.objects.update_or_create(
                    user=user_obj,
                    business_unit=bu_obj,
                    defaults={
                        "is_active": True,
                        "position": payload.get("position", "")
                    }
                )

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
                InternProfile.objects.filter(user=user_obj).update(supervisor=supervisor_obj)
                
    for row_num in sorted(row_results.keys()):
        results.append(row_results[row_num])
        
    return results
