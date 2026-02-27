NIVEIS = [
    (1, "Nível 1 - Iniciação"),
    (2, "Nível 2 - Básico"),
    (3, "Nível 3 - Intermediário"),
    (4, "Nível 4 - Intermediário Avançado"),
    (5, "Nível 5 - Avançado"),
]


from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re

def validar_cpf(cpf):
    cpf = re.sub(r'[^0-9]', '', cpf)

    if len(cpf) != 11:
        raise ValidationError("CPF deve conter 11 dígitos.")

    if cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.")

    # Validação do primeiro dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        raise ValidationError("CPF inválido.")

    # Segundo dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        raise ValidationError("CPF inválido.")

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    deve_trocar_senha = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username


class Turma(models.Model):
    nome = models.CharField(max_length=100)
    dia_semana = models.CharField(max_length=20)
    horario = models.TimeField()

    alunos = models.ManyToManyField(
        User,
        related_name='turmas_como_aluno',
        blank=True
    )

    def __str__(self):
        return f"{self.nome} - {self.dia_semana} {self.horario}"

class Aula(models.Model):
    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name='aulas'
    )

    data = models.DateField()
    
    professor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='aulas_ministradas'
    )

    class Meta:
        unique_together = ('turma', 'data')

    def __str__(self):
        return f"{self.turma} - {self.data}"


class Presenca(models.Model):
    aula = models.ForeignKey(
        Aula,
        on_delete=models.CASCADE,
        related_name='presencas'
    )

    aluno = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='presencas_recebidas'
    )

    presente = models.BooleanField(default=True)

    class Meta:
        unique_together = ('aula', 'aluno')

    def __str__(self):
        return f"{self.aluno} - {self.aula}"

class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    cpf = models.CharField(max_length=14, blank=True, null=True, validators=[validar_cpf])
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Aluno(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    cpf = models.CharField(max_length=14, blank=True, null=True, validators=[validar_cpf])
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Matricula(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)
    data_entrada = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('aluno', 'turma')



class Competencia(models.Model):
    nome = models.CharField(max_length=100)
    ativa = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class Avaliacao(models.Model):
    aluno = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="avaliacoes_recebidas"
    )

    professor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="avaliacoes_feitas"
    )

    data = models.DateField(auto_now_add=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ["-data"]

    def __str__(self):
        return f"Avaliação de {self.aluno} em {self.data}"


class NotaCompetencia(models.Model):
    avaliacao = models.ForeignKey(
        Avaliacao,
        on_delete=models.CASCADE,
        related_name="notas"
    )

    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.CASCADE
    )

    nivel = models.IntegerField(choices=NIVEIS)

    def __str__(self):
        return f"{self.competencia.nome} - {self.nivel}"

