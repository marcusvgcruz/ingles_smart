from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.email_utils import email_entrega_real_configurado, enviar_senha_provisoria, validar_configuracao_email


class Command(BaseCommand):
    help = "Test SMTP email delivery configured for the portal."

    def add_arguments(self, parser):
        parser.add_argument(
            "destinatario",
            nargs="?",
            default="",
            help="Recipient email (optional; uses EMAIL_HOST_USER if omitted).",
        )

    def handle(self, *args, **options):
        destinatario = (options["destinatario"] or settings.EMAIL_HOST_USER or "").strip()
        if not destinatario:
            raise CommandError("Provide a recipient or configure EMAIL_HOST_USER in .env.")

        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"FROM (effective): {settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"Real delivery: {email_entrega_real_configurado()}")

        ok_config, erro = validar_configuracao_email()
        if not ok_config:
            raise CommandError(erro)

        ok, erro = enviar_senha_provisoria(
            destinatario,
            "teste-portal-123",
            nome="Test",
            login_url=getattr(settings, "PORTAL_LOGIN_URL", None),
        )
        if ok:
            self.stdout.write(self.style.SUCCESS(f"Test email sent to {destinatario}."))
            self.stdout.write("Check logs/email.log and your spam folder.")
        else:
            raise CommandError(f"Send failed: {erro}")
