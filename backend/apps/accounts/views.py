from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import CanManageUsers
from .roles import is_administrative_user
from .serializers import (
    MeSerializer,
    ChangePasswordSerializer,
    SmartAcademyTokenObtainPairSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from .throttles import LoginRateThrottle

User = get_user_model()


class SmartAcademyTokenObtainPairView(TokenObtainPairView):
    serializer_class = SmartAcademyTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class MeAPIView(RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordAPIView(GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Mot de passe modifié avec succès."})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [CanManageUsers]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if is_administrative_user(self.request.user):
            return super().get_queryset()
        return super().get_queryset().none()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
