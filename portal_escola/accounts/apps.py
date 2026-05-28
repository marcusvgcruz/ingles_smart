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
                "EMAIL_BACKEND is in development mode — emails are NOT sent over the internet. "
                "Configure SMTP in the .env file and restart the server.",
                stacklevel=1,
            )
