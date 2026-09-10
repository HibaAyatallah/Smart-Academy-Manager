from django.core.management.base import BaseCommand

from apps.recruitment.analysis_pipeline import analyze_application_batch
from apps.recruitment.models import Application


class Command(BaseCommand):
    help = "Analyse les CV et calcule les matchings manquants des candidatures existantes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--application-id",
            type=int,
            help="Limiter le traitement à une candidature (recommandé pour un premier essai).",
        )
        parser.add_argument(
            "--force-matching",
            action="store_true",
            help="Recalculer les matchings même s’ils paraissent à jour.",
        )
        parser.add_argument(
            "--force-analysis",
            action="store_true",
            help=(
                "Réextraire les CV, y compris les analyses validées manuellement. "
                "Cette option remet la validation humaine à zéro."
            ),
        )

    def handle(self, *args, **options):
        applications = Application.objects.all()
        if options["application_id"] is not None:
            applications = applications.filter(pk=options["application_id"])
            if not applications.exists():
                self.stderr.write(self.style.ERROR("Candidature introuvable."))
                return
        summary = analyze_application_batch(
            applications,
            force_analysis=options["force_analysis"],
            force_matching=options["force_matching"] or options["force_analysis"],
        )
        labels = (
            ("total", "Candidatures totales"),
            ("already_analyzed", "Déjà analysées et matchées"),
            ("analyses_created", "Nouvelles analyses créées"),
            ("analyses_updated", "Analyses mises à jour"),
            ("matchings_created", "Matchings créés"),
            ("matchings_updated", "Matchings mis à jour"),
            ("without_cv", "Candidatures sans CV"),
            ("errors", "Erreurs"),
            ("ignored", "Candidatures ignorées"),
        )
        for key, label in labels:
            self.stdout.write(f"{label}: {summary[key]}")
        for detail in summary["details"]:
            self.stderr.write(
                f"Candidature #{detail['application_id']}: {detail['error']}"
            )
        if summary["errors"]:
            self.stdout.write(self.style.WARNING("Traitement terminé avec des erreurs isolées."))
        else:
            self.stdout.write(self.style.SUCCESS("Traitement historique terminé."))
