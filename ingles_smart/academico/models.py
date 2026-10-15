from datetime import date

from django.contrib.auth.models import User
from django.db import models

# validar_cpf permanece em accounts.models (referenciado por migrations historicas).
from accounts.models import validar_cpf


class Nivel(models.Model):

    nome = models.CharField(max_length=100)

    ativo = models.BooleanField(default=True)

    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "accounts_nivel"
        ordering = ["ordem"]

    def __str__(self):
        return self.nome


class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    cpf = models.CharField(max_length=14, blank=True, null=True, validators=[validar_cpf])
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    data_nascimento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "accounts_professor"

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Aluno(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    cpf = models.CharField(max_length=14, blank=True, null=True, validators=[validar_cpf])
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
        # NOVO 🔽
    data_nascimento = models.DateField(null=True, blank=True)

    # NOVO 🔽 (presencial/online)
    TIPO_ALUNO = [
        ("presencial", "In-person"),
        ("online", "Online"),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_ALUNO, default='presencial')

    # NOVO 🔽 (quem desativou)
    desativado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='alunos_desativados'
    )

    class Meta:
        db_table = "accounts_aluno"

    def idade(self):
        if not self.data_nascimento:
            return None

        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class BlockedPeriod(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    class Meta:
        db_table = "accounts_blockedperiod"
        verbose_name = "Blocked Period"
        verbose_name_plural = "Blocked Periods"


    
class ScheduleTemplate(models.Model):
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "accounts_scheduletemplate"
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
        db_table = "accounts_timeblock"
        verbose_name = "Time Block"
        verbose_name_plural = "Time Blocks"
        unique_together = ("template", "weekday", "start_time")

    
class Room(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "accounts_room"
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

    time_blocks = models.ManyToManyField(
    TimeBlock,
    related_name="turmas",
    blank=True
    )

    class Meta:
        db_table = "accounts_turma"

    def __str__(self):
        return self.name
    
class TurmaHorario(models.Model):
    DIAS_SEMANA = [
        ("segunda", "Monday"),
        ("terca", "Tuesday"),
        ("quarta", "Wednesday"),
        ("quinta", "Thursday"),
        ("sexta", "Friday"),
        ("sabado", "Saturday"),
        ("domingo", "Sunday"),
    ]

    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name="horarios")
    dia_semana = models.CharField(max_length=20, choices=DIAS_SEMANA)
    horario = models.TimeField()

    class Meta:
        db_table = "accounts_turmahorario"
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
        db_table = "accounts_matricula"
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
        db_table = "accounts_lesson"
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

    # 🔥 NOVO
    reposicao = models.BooleanField(default=False)

    # 🔥 NOVO
    data_reposicao = models.DateField(null=True, blank=True)
    reposicao_pendente = models.PositiveIntegerField(default=0)
    reposicao_registrada_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reposicoes_registradas",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_presenca"
        unique_together = ["lesson", "matricula"]

    def __str__(self):
        return f"{self.matricula.aluno} - {self.lesson}"


class ReposicaoAgendada(models.Model):
    presenca = models.ForeignKey(Presenca, on_delete=models.CASCADE, related_name="reposicoes_agendadas")
    data_agendada = models.DateField()
    horario_inicio = models.TimeField(null=True, blank=True)
    horario_fim = models.TimeField(null=True, blank=True)
    turma = models.ForeignKey(Turma, on_delete=models.SET_NULL, null=True, blank=True, related_name="reposicoes")
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name="reposicoes_geradas")
    observacao = models.CharField(max_length=255, blank=True, null=True)
    agendada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reposicoes_agendadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_reposicaoagendada"
        ordering = ["data_agendada", "-criado_em"]

    def __str__(self):
        return f"{self.presenca.matricula.aluno} - {self.data_agendada}"
