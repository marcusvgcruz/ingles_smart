"""
Envia para o Cloudinary arquivos que ainda estão só no disco local (pasta media/).

Use após configurar CLOUDINARY_URL no Render, com uma cópia da pasta media/ disponível
(ex.: backup antes do deploy, ou volume temporário).

    python manage.py enviar_midia_local_cloudinary
    python manage.py enviar_midia_local_cloudinary --dry-run
"""

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError

from accounts.models import (
    Estrategia,
    GamificationChallengeMedia,
    GamificationSubmissionMedia,
    Perfil,
    PostArquivo,
    PostImagem,
)
from accounts.storage import is_cloudinary_file

FILE_FIELD_MODELS = [
    (Perfil, ["avatar"]),
    (PostImagem, ["imagem"]),
    (PostArquivo, ["arquivo"]),
    (GamificationChallengeMedia, ["imagem", "arquivo"]),
    (GamificationSubmissionMedia, ["imagem", "arquivo"]),
    (
        Estrategia,
        [
            "pdf_portugues",
            "pdf_ingles",
            "study_sesh_portuguese",
            "study_sesh_english",
            "strategy_portuguese",
            "strategy_brazilian_english",
            "strategy_irish_english",
            "strategy_australian_english",
        ],
    ),
]


class Command(BaseCommand):
    help = (
        "Envia arquivos da pasta media/ local para o Cloudinary "
        "(quando o banco ainda aponta para caminhos locais)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas lista o que seria enviado, sem alterar nada.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "USE_CLOUDINARY", False):
            raise CommandError(
                "Cloudinary não está ativo. Defina CLOUDINARY_URL (ou credenciais separadas) "
                "antes de rodar este comando."
            )

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.is_dir():
            raise CommandError(f"Pasta de mídia não encontrada: {media_root}")

        local = FileSystemStorage(location=str(media_root))
        dry_run = options["dry_run"]
        enviados = 0
        ignorados = 0
        ausentes = 0

        for model, field_names in FILE_FIELD_MODELS:
            for obj in model.objects.all():
                for field_name in field_names:
                    field_file = getattr(obj, field_name)
                    if not field_file:
                        continue
                    if is_cloudinary_file(field_file):
                        ignorados += 1
                        continue
                    if not local.exists(field_file.name):
                        self.stdout.write(
                            self.style.WARNING(
                                f"Arquivo ausente no disco: {model.__name__} "
                                f"id={obj.pk} {field_name}={field_file.name}"
                            )
                        )
                        ausentes += 1
                        continue

                    label = f"{model.__name__} id={obj.pk} {field_name}={field_file.name}"
                    if dry_run:
                        self.stdout.write(f"[dry-run] Enviaria: {label}")
                        enviados += 1
                        continue

                    with local.open(field_file.name, "rb") as f:
                        field_file.save(field_file.name, File(f), save=False)
                    obj.save()
                    self.stdout.write(self.style.SUCCESS(f"Enviado: {label}"))
                    enviados += 1

        self.stdout.write(
            f"\nResumo: enviados={enviados}, já no Cloudinary={ignorados}, "
            f"ausentes no disco={ausentes}"
            + (" (simulação)" if dry_run else "")
        )
