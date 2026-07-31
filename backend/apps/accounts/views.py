from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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
    SmartAcademyTokenObtainPairSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from .throttles import LoginRateThrottle, SensitiveAccountRateThrottle
from .models import AccountSecurityLog
from apps.notifications.services import queue_email

User = get_user_model()


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

class UserImportViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperAdminOnly]
    
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def preview(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "Fichier manquant."}, status=400)
            
        # Optional: check file size (e.g. limit to 5MB)
        if file_obj.size > 5 * 1024 * 1024:
            return Response({"error": "Le fichier dépasse la taille maximale autorisée (5MB)."}, status=400)
            
        result = parse_and_validate_file(file_obj, file_obj.name)
        if "error" in result:
            return Response({"error": result["error"]}, status=400)
            
        return Response(result)

    @action(detail=False, methods=["post"])
    def confirm(self, request):
        valid_rows = request.data.get("valid_rows", [])
        create_missing_bus = request.data.get("create_missing_bus", False)
        
        if not valid_rows:
            return Response({"error": "Aucune ligne valide à importer."}, status=400)
            
        try:
            with transaction.atomic():
                results = execute_import(valid_rows, request.user, create_missing_bus=create_missing_bus)
            return Response({"results": results})
        except Exception as e:
            return Response({"error": f"Erreur lors de l'import: {str(e)}"}, status=400)
