from django.db import migrations, models
from django.db.models import Q


def limpar_flag_staff(apps, schema_editor):
    Perfil = apps.get_model("accounts", "Perfil")
    User = apps.get_model("auth", "User")
    staff_ids = User.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True)
    ).values_list("id", flat=True)
    Perfil.objects.filter(user_id__in=staff_ids).update(deve_trocar_senha=False)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_reposicaoagendada_horario_fim_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="perfil",
            name="deve_trocar_senha",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(limpar_flag_staff, migrations.RunPython.noop),
    ]
