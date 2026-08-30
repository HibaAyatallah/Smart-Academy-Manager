from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class PublicSubmissionRateThrottle(AnonRateThrottle):
    scope = "public_submission"


class CVPreviewRateThrottle(AnonRateThrottle):
    scope = "cv_preview"


class SensitiveAccountRateThrottle(UserRateThrottle):
    scope = "sensitive_account"
