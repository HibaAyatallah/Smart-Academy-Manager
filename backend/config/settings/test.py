from .local import *  # noqa: F403

# Keep production/development password security unchanged while making the
# isolated test suite fast and deterministic.
SECRET_KEY = "smart-academy-test-only-secret-key-not-for-production"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
RECRUITMENT_EMBEDDING_PROVIDER = "apps.recruitment.embeddings.DisabledEmbeddingProvider"

TEST_RUNNER = "config.test_runner.IsolatedSeedDataTestRunner"
