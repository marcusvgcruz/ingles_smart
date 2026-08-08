import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Create or update a superuser from environment variables "
        "(DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_EMAIL)."
    )

    def handle(self, *args, **options):
        username = (os.getenv("DJANGO_SUPERUSER_USERNAME") or "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD") or ""
        email = (os.getenv("DJANGO_SUPERUSER_EMAIL") or "").strip()

        if not username or not password:
            self.stdout.write(
                "ensure_superuser: environment variables not set — nothing to do."
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
                self.style.SUCCESS(f"Superuser '{username}' updated.")
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Superuser '{username}' created.")
        )
