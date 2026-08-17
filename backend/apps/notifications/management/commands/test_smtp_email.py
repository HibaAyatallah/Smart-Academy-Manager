import uuid
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from apps.notifications.services import send_templated_email


class Command(BaseCommand):
    help = "Send one explicit SMTP diagnostic email without storing an address in source code."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Explicit test recipient address.")
        parser.add_argument("--language", choices=("fr", "en"), default="fr")
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required acknowledgement that the recipient is authorised to receive the test.",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("Refusing to send without --confirm.")
        try:
            validate_email(options["to"])
        except ValidationError as exc:
            raise CommandError("The test recipient is not a valid email address.") from exc

        recipient = SimpleNamespace(
            email=options["to"],
            is_active=True,
            preferred_language=options["language"],
            first_name="SMTP",
            last_name="Test",
        )
        log = send_templated_email(
            recipient=recipient,
            event="notification",
            event_key=f"smtp-test:{uuid.uuid4()}",
            subject="Smart Academy SMTP test",
            context={"message": "Smart Academy SMTP configuration test."},
        )
        if not log or log.status != "SENT":
            error_code = log.error_code if log else "NO_DELIVERY_LOG"
            raise CommandError(f"SMTP test failed ({error_code}). Check the server logs.")
        self.stdout.write(self.style.SUCCESS(f"SMTP test sent; delivery log #{log.pk}."))
