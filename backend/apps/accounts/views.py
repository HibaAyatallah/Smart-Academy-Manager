import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers, viewsets
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from .permissions import CanManageUsers
from .roles import is_super_admin
from .serializers import (
    MeSerializer,
    ChangePasswordSerializer,
    ContactDetailsSerializer,
    PreferredLanguageSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SmartAcademyTokenObtainPairSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from .throttles import LoginRateThrottle, SensitiveAccountRateThrottle
from .models import AccountSecurityLog
from apps.notifications.services import queue_email

User = get_user_model()
logger = logging.getLogger(__name__)


class SmartAcademyTokenObtainPairView(TokenObtainPairView):
    serializer_class = SmartAcademyTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class MeAPIView(RetrieveAPIView):
    """All authenticated users can read their own profile."""
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordAPIView(GenericAPIView):
    """All authenticated users can change their own password."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [SensitiveAccountRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        AccountSecurityLog.objects.create(
            actor=user, action="PASSWORD_CHANGED", metadata={"source": "self_service"}
        )
        queue_email(recipient=user, event="password.changed", event_key=f"password-changed:{user.pk}:{user.updated_at.isoformat()}", context={"message":"Votre mot de passe vient d'être modifié."})
        return Response({"detail": "Mot de passe modifié avec succès."})


PASSWORD_RESET_RESPONSE = "Si cette adresse est associée à un compte, un email de réinitialisation vous a été envoyé."


class PasswordResetRequestAPIView(GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_email(), is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_path = f"/reset-password?token={uid}.{token}"
            queue_email(
                recipient=user,
                event="password.reset",
                event_key=f"password-reset:{user.pk}:{token}",
                subject="Réinitialisation de votre mot de passe Smart Academy",
                context={
                    "message": "Une demande de réinitialisation de votre mot de passe a été reçue.",
                    "link": reset_path,
                    "button_label": "Oui, c’est moi",
                    "template_name": "emails/password_reset.html",
                },
            )
            AccountSecurityLog.objects.create(actor=user, action="PASSWORD_RESET_REQUESTED", metadata={})
        return Response({"detail": PASSWORD_RESET_RESPONSE})


class PasswordResetTokenAPIView(GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    serializer_class = PasswordResetConfirmSerializer

    def get(self, request, uid, token):
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError, UnicodeDecodeError):
            return Response({"valid": False}, status=400)
        if not default_token_generator.check_token(user, token):
            return Response({"valid": False}, status=400)
        return Response({"valid": True})


class PasswordResetConfirmAPIView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        self._revoke_sessions_and_tokens(user)
        AccountSecurityLog.objects.create(actor=user, action="PASSWORD_RESET_COMPLETED", metadata={})
        queue_email(
            recipient=user,
            event="password.reset.completed",
            event_key=f"password-reset-completed:{user.pk}:{user.password[-16:]}",
            subject="Votre mot de passe Smart Academy a été modifié",
            context={
                "message": "Votre mot de passe Smart Academy a été modifié.",
                "template_name": "emails/password_reset_completed.html",
            },
        )
        return Response({"detail": "Votre mot de passe a été modifié avec succès."})

    @staticmethod
    def _revoke_sessions_and_tokens(user):
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)
        for session in Session.objects.all():
            try:
                if str(session.get_decoded().get("_auth_user_id")) == str(user.pk):
                    session.delete()
            except Exception:
                continue


class ContactDetailsAPIView(GenericAPIView):
    serializer_class = ContactDetailsSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [SensitiveAccountRateThrottle]

    def patch(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, changed = serializer.save()
        if changed:
            AccountSecurityLog.objects.create(
                actor=user,
                action="CONTACT_DETAILS_CHANGED",
                metadata={"changed_fields": changed},
            )
            if "email" in changed:
                queue_email(recipient=user, event="email.changed", event_key=f"email-changed:{user.pk}:{user.updated_at.isoformat()}", context={"message":"Votre adresse e-mail de connexion a été modifiée."})
        return Response(MeSerializer(user).data)


class PreferredLanguageAPIView(GenericAPIView):
    serializer_class = PreferredLanguageSerializer
    permission_classes = [IsAuthenticated]
    def patch(self, request):
        serializer = self.get_serializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """User management — Super Admin only.

    HR must NOT access this viewset. HR uses dedicated /api/hr/ endpoints
    for the restricted read-only data they are authorised to see.
    """
    queryset = User.objects.all()
    permission_classes = [CanManageUsers]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["email", "created_at", "role"]
    ordering = ["email"]

    def get_queryset(self):
        if is_super_admin(self.request.user):
            return User.objects.all()
        return User.objects.none()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from .permissions import IsSuperAdminOnly
from .services.bulk_import import parse_and_validate_file, execute_import
from django.db import transaction

class UserImportSchemaSerializer(serializers.Serializer):
    """Schema marker for import preview and confirmation actions."""


class UserImportViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperAdminOnly]
    serializer_class = UserImportSchemaSerializer
    
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def preview(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "Fichier manquant."}, status=400)
            
        # Optional: check file size (e.g. limit to 5MB)
        if file_obj.size > 5 * 1024 * 1024:
            return Response({"error": "Le fichier dépasse la taille maximale autorisée (5MB)."}, status=400)
            
        try:
            result = parse_and_validate_file(file_obj, file_obj.name)
        except Exception:
            # A malformed workbook must be reported as a validation error and
            # must never escape the preview endpoint as an HTTP 500.
            return Response(
                {"error": "Le fichier contient une structure de colonnes invalide."},
                status=400,
            )
        if "error" in result:
            return Response({"error": result["error"]}, status=400)
            
        return Response(result)

    @action(detail=False, methods=["post"])
    def confirm(self, request):
        valid_rows = request.data.get("valid_rows", [])
        
        if not valid_rows:
            return Response({"error": "Aucune ligne valide à importer."}, status=400)
            
        try:
            with transaction.atomic():
                results = execute_import(valid_rows, request.user)
            return Response({"results": results})
        except ValueError as exc:
            logger.warning("Bulk import rejected error_type=%s", exc.__class__.__name__)
            return Response({"error": "Les données d'import sont incohérentes."}, status=400)
        except Exception as exc:
            logger.error("Bulk import confirmation failed error_type=%s", exc.__class__.__name__)
            return Response({"error": "L'import n'a pas pu être finalisé."}, status=500)
