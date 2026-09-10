from django.core.management.base import BaseCommand, CommandError

from apps.recruitment.rag.errors import RAGError
from apps.recruitment.rag.retriever import retrieve_cv_context


class Command(BaseCommand):
    help = "Recherche des passages CV pertinents sans générer de réponse LLM."

    def add_arguments(self, parser):
        parser.add_argument("application_id", type=int)
        parser.add_argument("query")
        parser.add_argument("--top-k", type=int, default=5)

    def handle(self, *args, **options):
        try:
            rows = retrieve_cv_context(
                options["query"],
                application_id=options["application_id"],
                top_k=options["top_k"],
            )
        except RAGError as exc:
            raise CommandError(f"{exc.code}: {exc}") from exc
        if not rows:
            self.stdout.write("Aucun passage trouvé.")
            return
        for position, row in enumerate(rows, start=1):
            metadata = row["metadata"]
            self.stdout.write(
                f"#{position} score={row['score']:.2f}% section={metadata.get('section')} "
                f"application={metadata.get('application_id')} document={metadata.get('application_document_id')}"
            )
            self.stdout.write(row["text"])
