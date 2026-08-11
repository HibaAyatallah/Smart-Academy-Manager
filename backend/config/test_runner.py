from django.test.runner import DiscoverRunner


class IsolatedSeedDataTestRunner(DiscoverRunner):
    """Keep migration-created reference data out of isolated unit tests.

    Production databases retain the official Business Units created by the data
    migration. Tests, however, must start from an empty business-data boundary so
    each test case can create and count its own fixtures deterministically.
    """

    def setup_databases(self, **kwargs):
        old_config = super().setup_databases(**kwargs)

        from apps.business_units.models import BusinessUnit

        BusinessUnit.objects.all().delete()
        return old_config
