from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.db.models import Q
import re


def validar_cpf(cpf):
    cpf = re.sub(r'[^0-9]', '', cpf)

    if len(cpf) != 11:
        raise ValidationError("CPF must contain 11 digits.")

    if cpf == cpf[0] * 11:
        raise ValidationError("Invalid CPF.")

    # Validação do primeiro dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        raise ValidationError("Invalid CPF.")

    # Segundo dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        raise ValidationError("Invalid CPF.")


def matriculas_ativas(aluno):
    # Import local para evitar import circular entre apps (Matricula vive em academico).
    from academico.models import Matricula

    hoje = timezone.now().date()

    return Matricula.objects.filter(
        aluno=aluno,
        data_inicio__lte=hoje
    ).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gte=hoje)
    )


class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    deve_trocar_senha = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to="profiles/avatars/", null=True, blank=True)

    def __str__(self):
        return self.user.username
