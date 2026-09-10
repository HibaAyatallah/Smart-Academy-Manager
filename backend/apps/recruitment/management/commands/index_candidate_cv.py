from django.core.management.base import BaseCommand, CommandError

from apps.recruitment.rag.errors import RAGError
from apps.recruitment.rag.indexer import index_candidate_cv


class Command(BaseCommand):
    help = "Indexe le CV analysé d’une candidature dans le vector store RAG."

    def add_arguments(self, parser):
        parser.add_argument("application_id", type=int)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        try:
            result = index_candidate_cv(options["application_id"], force=options["force"])
        except RAGError as exc:
            raise CommandError(f"{exc.code}: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(
            f"{result['status']} — candidature {result['application_id']} — {result['chunk_count']} chunk(s)"
        ))
