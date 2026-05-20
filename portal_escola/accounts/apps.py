from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals

        from django.conf import settings

        from accounts.email_utils import email_entrega_real_configurado

        if not email_entrega_real_configurado():
            import warnings

            warnings.warn(
                "EMAIL_BACKEND em modo desenvolvimento — e-mails NÃO saem pela internet. "
                "Configure SMTP no arquivo .env e reinicie o servidor.",
                stacklevel=1,
            )
