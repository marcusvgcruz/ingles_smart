from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrar_turmas_para_horarios(apps, schema_editor):
    Turma = apps.get_model("accounts", "Turma")
    TurmaHorario = apps.get_model("accounts", "TurmaHorario")
    TurmaHorarioAluno = apps.get_model("accounts", "TurmaHorarioAluno")
    Aula = apps.get_model("accounts", "Aula")

    for turma in Turma.objects.all():
        dia_original = (turma.dia_semana or "").strip().lower()
        mapeamento = {
            "segunda": "segunda",
            "segunda-feira": "segunda",
            "terca": "terca",
            "terça": "terca",
            "terca-feira": "terca",
            "terça-feira": "terca",
            "quarta": "quarta",
            "quarta-feira": "quarta",
            "quinta": "quinta",
            "quinta-feira": "quinta",
            "sexta": "sexta",
            "sexta-feira": "sexta",
            "sabado": "sabado",
            "sábado": "sabado",
            "domingo": "domingo",
        }
        dia_semana = mapeamento.get(dia_original, "segunda")

        horario = TurmaHorario.objects.create(
            turma=turma,
            dia_semana=dia_semana,
            horario=turma.horario,
        )

        for aluno in turma.alunos.all():
            TurmaHorarioAluno.objects.get_or_create(turma_horario=horario, aluno=aluno)

        Aula.objects.filter(turma=turma).update(turma_horario=horario)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_professor_cpf_professor_endereco_professor_telefone"),
    ]

    operations = [
        migrations.CreateModel(
            name="TurmaHorario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "dia_semana",
                    models.CharField(
                        choices=[
                            ("segunda", "Segunda-feira"),
                            ("terca", "Terça-feira"),
                            ("quarta", "Quarta-feira"),
                            ("quinta", "Quinta-feira"),
                            ("sexta", "Sexta-feira"),
                            ("sabado", "Sábado"),
                            ("domingo", "Domingo"),
                        ],
                        max_length=20,
                    ),
                ),
                ("horario", models.TimeField()),
                (
                    "turma",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="horarios", to="accounts.turma"),
                ),
            ],
            options={"ordering": ["dia_semana", "horario"], "unique_together": {("turma", "dia_semana", "horario")}},
        ),
        migrations.CreateModel(
            name="TurmaHorarioAluno",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vinculos_turma", to=settings.AUTH_USER_MODEL)),
                (
                    "turma_horario",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vinculos", to="accounts.turmahorario"),
                ),
            ],
            options={"unique_together": {("turma_horario", "aluno")}},
        ),
        migrations.AddField(
            model_name="aula",
            name="turma_horario",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="aulas", to="accounts.turmahorario"),
        ),
        migrations.RunPython(migrar_turmas_para_horarios, noop),
        migrations.RemoveField(model_name="aula", name="turma"),
        migrations.AlterField(
            model_name="aula",
            name="turma_horario",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="aulas", to="accounts.turmahorario"),
        ),
        migrations.AlterUniqueTogether(name="aula", unique_together={("turma_horario", "data")}),
        migrations.RemoveField(model_name="turma", name="alunos"),
        migrations.RemoveField(model_name="turma", name="dia_semana"),
        migrations.RemoveField(model_name="turma", name="horario"),
    ]
