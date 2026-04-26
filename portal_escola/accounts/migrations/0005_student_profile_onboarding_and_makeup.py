# Generated manually for project updates
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_post_is_fixo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="aluno",
            name="data_nascimento",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="professor",
            name="data_nascimento",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="presenca",
            name="reposicao_pendente",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="presenca",
            name="salvo_por",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="presencas_salvas", to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name="OnboardingItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=120, unique=True)),
                ("ativo", models.BooleanField(default=True)),
                ("ordem", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["ordem", "nome"]},
        ),
        migrations.CreateModel(
            name="OnboardingAlunoItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("concluido", models.BooleanField(default=False)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="onboarding_status", to="accounts.aluno")),
                ("atualizado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="accounts.onboardingitem")),
            ],
            options={"unique_together": {("aluno", "item")}},
        ),
        migrations.RunPython(
            lambda apps, schema_editor: [
                apps.get_model("accounts", "OnboardingItem").objects.get_or_create(nome=nome, defaults={"ordem": idx})
                for idx, nome in enumerate([
                    "Reviewed on Google",
                    "Subscribed on YouTube",
                    "Completed first interview",
                    "Received material",
                ], start=1)
            ],
            migrations.RunPython.noop,
        ),
    ]
