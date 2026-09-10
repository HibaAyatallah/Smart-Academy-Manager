from django.core.management.base import BaseCommand, CommandError

from apps.recruitment.embeddings import EmbeddingError, OllamaEmbeddingProvider


class Command(BaseCommand):
    help = "Vérifie manuellement que le modèle d’embedding recrutement Ollama fonctionne."

    def add_arguments(self, parser):
        parser.add_argument(
            "--text",
            default="Développeur Python Django pour API backend",
            help="Texte de diagnostic envoyé au modèle d’embedding.",
        )

    def handle(self, *args, **options):
        try:
            vector = OllamaEmbeddingProvider().embed(options["text"])
        except (EmbeddingError, ValueError) as exc:
            raise CommandError(f"Échec embedding ({getattr(exc, 'code', 'configuration_error')}): {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Embedding valide : {len(vector)} dimensions."))
