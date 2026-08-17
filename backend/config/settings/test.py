from .local import *  # noqa: F403

# Keep production/development password security unchanged while making the
# isolated test suite fast and deterministic.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

TEST_RUNNER = "config.test_runner.IsolatedSeedDataTestRunner"
