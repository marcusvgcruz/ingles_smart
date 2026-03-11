from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
import re
import datetime


NIVEIS = [
    (1, "Nível 1 - Iniciação"),
    (2, "Nível 2 - Básico"),
    (3, "Nível 3 - Intermediário"),
    (4, "Nível 4 - Intermediário Avançado"),
    (5, "Nível 5 - Avançado"),
]

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


class BlockedPeriod(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    class Meta:
        verbose_name = "Blocked Period"
        verbose_name_plural = "Blocked Periods"


    
class ScheduleTemplate(models.Model):
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Schedule Template"
        verbose_name_plural = "Schedule Templates"

class TimeBlock(models.Model):
    DAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    template = models.ForeignKey(
        ScheduleTemplate,
        on_delete=models.CASCADE,
        related_name="blocks"
    )

    weekday = models.IntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.get_weekday_display()} {self.start_time} - {self.end_time}"

    class Meta:
        verbose_name = "Time Block"
        verbose_name_plural = "Time Blocks"
        unique_together = ("template", "weekday", "start_time")

    
class Room(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Room"
        verbose_name_plural = "Rooms"

class Turma(models.Model):
    name = models.CharField(max_length=100)

    room = models.ForeignKey(
    Room,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="turmas"
    )


    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    time_blocks = models.ManyToManyField(
    TimeBlock,
    related_name="turmas",
    blank=True
    )

    
    def __str__(self):
        return f"{self.name} • {self.start_date}"
    
class TurmaHorario(models.Model):
    DIAS_SEMANA = [
        ("segunda", "Segunda-feira"),
        ("terca", "Terça-feira"),
        ("quarta", "Quarta-feira"),
        ("quinta", "Quinta-feira"),
        ("sexta", "Sexta-feira"),
        ("sabado", "Sábado"),
        ("domingo", "Domingo"),
    ]

    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name="horarios")
    dia_semana = models.CharField(max_length=20, choices=DIAS_SEMANA)
    horario = models.TimeField()

    class Meta:
        unique_together = ("turma", "dia_semana", "horario")
        ordering = ["dia_semana", "horario"]

    def __str__(self):
        return f"{self.get_dia_semana_display()} - {self.horario.strftime('%H:%M')}"
    
class Matricula(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)

    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('aluno', 'turma', 'data_inicio')

    def ativa_na_data(self, data):
        if self.data_inicio <= data:
            if self.data_fim:
                return data <= self.data_fim
            return True
        return False
    
    def __str__(self):
        return f"{self.student} - {self.class_group}"
    
class Lesson(models.Model):
    class_group = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name="lessons"
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons"
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.class_group} - {self.date}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["date", "start_time", "room"],
                name="unique_room_time"
            )
        ]
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"
        ordering = ["date"]

class Presenca(models.Model):

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="presencas"
    )

    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.CASCADE
        )

    presente = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["lesson", "matricula"]

    def __str__(self):
        return f"{self.matricula.aluno} - {self.lesson}"