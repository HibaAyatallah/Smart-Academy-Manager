from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class PublicSubmissionRateThrottle(AnonRateThrottle):
    scope = "public_submission"