"""
Remove arquivos no Cloudinary que não estão ligados a nenhum registro do banco.

Equivalente a `deleteorphanedmedia` do django-cloudinary-storage, com nome em português.

    python manage.py limpar_midia_orfa
    python manage.py limpar_midia_orfa --noinput

No Render (plano pago), agende um Cron Job com o mesmo comando periodicamente.
"""

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Remove imagens/arquivos órfãos no Cloudinary (sem referência no banco de dados)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Não pedir confirmação.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "USE_CLOUDINARY", False):
            raise CommandError(
                "Cloudinary não está ativo. Este comando só funciona com CLOUDINARY_URL configurado."
            )

        self.stdout.write(
            "Removendo mídia órfã no Cloudinary (arquivos sem registro no banco)…"
        )
        call_command(
            "deleteorphanedmedia",
            noinput=options["noinput"],
        )
        self.stdout.write(self.style.SUCCESS("Limpeza concluída."))
