import logging
import secrets
import string
import unicodedata
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.accounts.choices import UserRole
from apps.business_units.models import BusinessUnitMembership
from apps.recruitment.models import InternProfile, EmployeeProfile
from apps.trainings.models import ClientProfile

User = get_user_model()
logger = logging.getLogger(__name__)


def generate_secure_password(length=12):
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= 2):
            break
    return password


def normalize_text(text: str) -> str:
    """Normalize accents, spaces, apostrophes for email generation."""
    if not text:
        return ""
    text = text.lower().strip()
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    text = ''.join(c for c in text if c.isalnum())
    return text


def generate_professional_email(first_name: str, last_name: str) -> str:
    """
    Generate a professional email: firstname.lastname@finatech.com
    Handles collisions by appending 2, 3, etc.
    """
    first = normalize_text(first_name) or "user"
    last = normalize_text(last_name) or "finatech"
    
    base_email = f"{first}.{last}@finatech.com"
    email = base_email
    counter = 2
    
    while User.objects.filter(email=email).exists():
        email = f"{first}.{last}{counter}@finatech.com"
        counter += 1
        
    return email


def generate_account_for_user(payload: dict, actor=None) -> dict:
    """
    Creates or updates the User, generates credentials, and creates the appropriate profile.
    
    Payload should contain:
    - first_name
    - last_name
    - contact_email (personal email)
    - phone_number
    - role (UserRole choice)
    - business_unit (BusinessUnit instance or None)
    - position (str)
    - supervisor (User instance or None)
    - school (str)
    - specialization (str)
    - internship_type (str)
    - paid (bool)
    - internship_start (date)
    - internship_end (date)
    - subject_title (str)
    
    Returns a dict containing the generated credentials and user instance.
    """
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    contact_email = payload.get("contact_email")
    role = payload.get("role", UserRole.EMPLOYEE)
    business_unit = payload.get("business_unit")
    
    user = None
    if contact_email:
        user = User.objects.filter(contact_email=contact_email).first()
        if not user:
            user = User.objects.filter(email=contact_email).first()
            
    is_new = False
    temp_password = None
    generated_email = None

    with transaction.atomic():
        if not user:
            is_new = True
            generated_email = generate_professional_email(first_name, last_name)
            temp_password = generate_secure_password()
            
            user = User(
                email=generated_email,
                first_name=first_name,
                last_name=last_name,
                contact_email=contact_email,
                role=role,
                phone_number=payload.get("phone_number", ""),
                must_change_password=True,
                is_active=True
            )
            user.set_password(temp_password)
            user.save()
        else:
            user.role = role
            user.is_active = True
            
            if not user.email.endswith("@finatech.com"):
                if not user.contact_email:
                    user.contact_email = user.email
                generated_email = generate_professional_email(first_name or user.first_name, last_name or user.last_name)
                temp_password = generate_secure_password()
                user.email = generated_email
                user.must_change_password = True
                user.set_password(temp_password)
                
            user.save(update_fields=["role", "is_active", "email", "contact_email", "must_change_password", "password"])

        if role == UserRole.INTERN:
            InternProfile.objects.update_or_create(
                user=user,
                defaults={
                    "school": payload.get("school", ""),
                    "specialization": payload.get("specialization", ""),
                    "internship_type": payload.get("internship_type", ""),
                    "paid": payload.get("paid", False),
                    "business_unit": business_unit,
                    "supervisor": payload.get("supervisor"),
                    "subject_title": payload.get("subject_title", ""),
                    "internship_start": payload.get("internship_start"),
                    "internship_end": payload.get("internship_end"),
                }
            )
        elif role == UserRole.CLIENT:
            ClientProfile.objects.update_or_create(user=user)
        elif role in [UserRole.EMPLOYEE, UserRole.BU_MANAGER, UserRole.TRAINER_TUTOR]:
            EmployeeProfile.objects.update_or_create(user=user)
            
        if business_unit and role != UserRole.CLIENT:
            BusinessUnitMembership.objects.update_or_create(
                user=user,
                business_unit=business_unit,
                defaults={
                    "is_active": True,
                    "position": payload.get("position", "")
                }
            )

    return {
        "user": user,
        "is_new": is_new,
        "email": user.email,
        "temporary_password": temp_password,
    }
