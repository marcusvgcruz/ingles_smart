"""Limpa HTML perigoso dos posts já gravados (XSS armazenado).

Uso:
    python manage.py sanitizar_posts --dry-run   # só mostra o que mudaria
    python manage.py sanitizar_posts             # aplica
"""

from django.core.management.base import BaseCommand

from accounts.html_sanitize import sanitizar_html
from feed.models import Post


class Command(BaseCommand):
    help = "Sanitiza o HTML dos posts existentes, removendo scripts/eventos/URLs perigosas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quantos posts seriam alterados, sem gravar.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total = 0
        alterados = 0

        for post in Post.objects.all().iterator():
            total += 1
            original = post.conteudo or ""
            limpo = sanitizar_html(original)
            if limpo != original:
                alterados += 1
                self.stdout.write(f"  post {post.id}: conteudo alterado")
                if not dry_run:
                    post.conteudo = limpo
                    post.save(update_fields=["conteudo"])

        acao = "seriam alterados" if dry_run else "alterados"
        self.stdout.write(
            self.style.SUCCESS(f"{total} posts verificados · {alterados} {acao}")
        )
