import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Cria ou atualiza um superusuário a partir de variáveis de ambiente "
        "(DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_EMAIL)."
    )

    def handle(self, *args, **options):
        username = (os.getenv("DJANGO_SUPERUSER_USERNAME") or "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD") or ""
        email = (os.getenv("DJANGO_SUPERUSER_EMAIL") or "").strip()

        if not username or not password:
            self.stdout.write(
                "ensure_superuser: variáveis não definidas — nada a fazer."
            )
            return

        User = get_user_model()
        user = User.objects.filter(username=username).first()

        if user:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            if email:
                user.email = email
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Superusuário '{username}' atualizado.")
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Superusuário '{username}' criado.")
        )
