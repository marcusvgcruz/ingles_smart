from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.email_utils import email_entrega_real_configurado, enviar_senha_provisoria, validar_configuracao_email


class Command(BaseCommand):
    help = "Testa o envio de e-mail SMTP configurado no portal."

    def add_arguments(self, parser):
        parser.add_argument(
            "destinatario",
            nargs="?",
            default="",
            help="E-mail de destino (opcional; usa EMAIL_HOST_USER se omitido).",
        )

    def handle(self, *args, **options):
        destinatario = (options["destinatario"] or settings.EMAIL_HOST_USER or "").strip()
        if not destinatario:
            raise CommandError("Informe o destinatario ou configure EMAIL_HOST_USER no .env.")

        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"FROM (efetivo): {settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"Entrega real: {email_entrega_real_configurado()}")

        ok_config, erro = validar_configuracao_email()
        if not ok_config:
            raise CommandError(erro)

        ok, erro = enviar_senha_provisoria(
            destinatario,
            "teste-portal-123",
            nome="Teste",
            login_url=getattr(settings, "PORTAL_LOGIN_URL", None),
        )
        if ok:
            self.stdout.write(self.style.SUCCESS(f"E-mail de teste enviado para {destinatario}."))
            self.stdout.write("Confira logs/email.log e a caixa de spam.")
        else:
            raise CommandError(f"Falha no envio: {erro}")
