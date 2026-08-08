from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def criar_estrategias_fixas(apps, schema_editor):
    Estrategia = apps.get_model("accounts", "Estrategia")
    for n in range(1, 11):
        Estrategia.objects.get_or_create(
            numero=n,
            defaults={
                "titulo": f"Strategy {n}",
                "descricao": "",
            },
        )


def reverter_estrategias(apps, schema_editor):
    Estrategia = apps.get_model("accounts", "Estrategia")
    Estrategia.objects.filter(numero__lte=10).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_perfil_deve_trocar_senha_default"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Estrategia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.PositiveSmallIntegerField(unique=True)),
                ("titulo", models.CharField(max_length=255)),
                ("descricao", models.TextField(blank=True)),
                ("pdf_portugues", models.FileField(blank=True, null=True, upload_to="estrategias/pdf/")),
                ("pdf_ingles", models.FileField(blank=True, null=True, upload_to="estrategias/pdf/")),
                ("audio1", models.FileField(blank=True, null=True, upload_to="estrategias/audio/")),
                ("audio2", models.FileField(blank=True, null=True, upload_to="estrategias/audio/")),
                ("audio3", models.FileField(blank=True, null=True, upload_to="estrategias/audio/")),
                ("audio4", models.FileField(blank=True, null=True, upload_to="estrategias/audio/")),
            ],
            options={
                "ordering": ["numero"],
                "verbose_name_plural": "Estratégias",
            },
        ),
        migrations.CreateModel(
            name="EstrategiaAlunoAcesso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("liberado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "aluno",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="estrategias_acesso",
                        to="accounts.aluno",
                    ),
                ),
                (
                    "estrategia",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="acessos",
                        to="accounts.estrategia",
                    ),
                ),
                (
                    "liberado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="estrategias_liberadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["aluno__user__first_name", "aluno__user__last_name"],
                "unique_together": {("estrategia", "aluno")},
            },
        ),
        migrations.RunPython(criar_estrategias_fixas, reverter_estrategias),
    ]
