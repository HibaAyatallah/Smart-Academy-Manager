from drf_spectacular.extensions import OpenApiAuthenticationExtension


class MandatoryPasswordChangeJWTScheme(OpenApiAuthenticationExtension):
    target_class = (
        "apps.accounts.authentication.MandatoryPasswordChangeJWTAuthentication"
    )
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
