from django.db import migrations, models


def renomear_titulos_para_ingles(apps, schema_editor):
    Estrategia = apps.get_model("accounts", "Estrategia")
    for e in Estrategia.objects.all():
        if e.titulo.startswith("Estratégia "):
            e.titulo = f"Strategy {e.numero}"
            e.save(update_fields=["titulo"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_estrategia_estrategiaalunoacesso"),
    ]

    operations = [
        migrations.RenameField(
            model_name="estrategia",
            old_name="audio1",
            new_name="study_sesh_portuguese",
        ),
        migrations.RenameField(
            model_name="estrategia",
            old_name="audio2",
            new_name="study_sesh_english",
        ),
        migrations.RenameField(
            model_name="estrategia",
            old_name="audio3",
            new_name="strategy_portuguese",
        ),
        migrations.RenameField(
            model_name="estrategia",
            old_name="audio4",
            new_name="strategy_brazilian_english",
        ),
        migrations.AddField(
            model_name="estrategia",
            name="strategy_irish_english",
            field=models.FileField(blank=True, null=True, upload_to="estrategias/audio/"),
        ),
        migrations.AddField(
            model_name="estrategia",
            name="strategy_australian_english",
            field=models.FileField(blank=True, null=True, upload_to="estrategias/audio/"),
        ),
        migrations.RunPython(renomear_titulos_para_ingles, migrations.RunPython.noop),
    ]
