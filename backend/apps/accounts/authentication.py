from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


PASSWORD_CHANGE_ALLOWED_URLS = {
    "auth_me",
    "auth_change_password",
}


class MandatoryPasswordChangeJWTAuthentication(JWTAuthentication):
    """Keep temporary-password accounts outside business APIs."""

    def authenticate(self, request):
        authenticated = super().authenticate(request)
        if authenticated is None:
            return None

        user, validated_token = authenticated
        url_name = getattr(getattr(request, "resolver_match", None), "url_name", None)
        if user.must_change_password and url_name not in PASSWORD_CHANGE_ALLOWED_URLS:
            raise PermissionDenied(
                detail="Vous devez modifier votre mot de passe temporaire avant de continuer.",
                code="password_change_required",
            )
        return user, validated_token
