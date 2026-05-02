from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
import re
from datetime import date
from ckeditor.fields import RichTextField
from django.utils import timezone
from django.db.models import Q

def matriculas_ativas(aluno):
    hoje = timezone.now().date()

    return Matricula.objects.filter(
        aluno=aluno,
        data_inicio__lte=hoje
    ).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gte=hoje)
    )

class Nivel(models.Model):

    nome = models.CharField(max_length=100)

    ativo = models.BooleanField(default=True)

    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem"]

    def __str__(self):
        return self.nome

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
    avatar = models.ImageField(upload_to="profiles/avatars/", null=True, blank=True)

    def __str__(self):
        return self.user.username

class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    cpf = models.CharField(max_length=14, blank=True, null=True, validators=[validar_cpf])
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    data_nascimento = models.DateField(null=True, blank=True)

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

    def idade(self):
        if not self.data_nascimento:
            return None

        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

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

    nivel = models.ForeignKey(
    Nivel,
    on_delete=models.CASCADE
    )

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
        unique_together = ["lesson", "matricula"]

    def __str__(self):
        return f"{self.matricula.aluno} - {self.lesson}"
    
class Post(models.Model):
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    conteudo = RichTextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    is_fixo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.autor} - {self.criado_em}"


class PostImagem(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='imagens')
    imagem = models.ImageField(upload_to='feed/imagens/')


class PostArquivo(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='arquivos')
    arquivo = models.FileField(upload_to='feed/arquivos/')
    nome = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        if not self.nome:
            self.nome = self.arquivo.name
        super().save(*args, **kwargs)

class TarefaAluno(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='tarefas')

    nome = models.CharField(max_length=255)
    concluido = models.BooleanField(default=False)
    data_conclusao = models.DateTimeField(null=True, blank=True)


class OnboardingItem(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class OnboardingAlunoItem(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="onboarding_itens")
    item = models.ForeignKey(OnboardingItem, on_delete=models.CASCADE, related_name="status_alunos")
    concluido = models.BooleanField(default=False)
    atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="onboarding_updates",
    )

    class Meta:
        unique_together = ("aluno", "item")
        ordering = ["item__ordem", "item__nome"]

    def __str__(self):
        return f"{self.aluno} - {self.item.nome}"


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
        ordering = ["data_agendada", "-criado_em"]

    def __str__(self):
        return f"{self.presenca.matricula.aluno} - {self.data_agendada}"


class GamificationChallenge(models.Model):
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    pontos = models.PositiveIntegerField(default=10)
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="desafios_criados")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo


class GamificationSubmission(models.Model):
    challenge = models.ForeignKey(GamificationChallenge, on_delete=models.CASCADE, related_name="submissoes")
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="submissoes_gamificacao")
    comentario = models.CharField(max_length=255, blank=True, null=True)
    concluido = models.BooleanField(default=False)
    validado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissoes_validadas",
    )
    validado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("challenge", "aluno")
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.aluno} - {self.challenge}"


class GamificationChallengeMedia(models.Model):
    challenge = models.ForeignKey(GamificationChallenge, on_delete=models.CASCADE, related_name="midias")
    imagem = models.ImageField(upload_to="gamification/challenges/images/", null=True, blank=True)
    arquivo = models.FileField(upload_to="gamification/challenges/files/", null=True, blank=True)
    video_url = models.URLField(blank=True, null=True)


class GamificationSubmissionMedia(models.Model):
    submission = models.ForeignKey(GamificationSubmission, on_delete=models.CASCADE, related_name="midias")
    imagem = models.ImageField(upload_to="gamification/submissions/images/", null=True, blank=True)
    arquivo = models.FileField(upload_to="gamification/submissions/files/", null=True, blank=True)
    video_url = models.URLField(blank=True, null=True)


class Contract(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="contratos")
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    inicio = models.DateField()
    fim = models.DateField(null=True, blank=True)
    observacao = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-inicio"]

    def __str__(self):
        return f"{self.aluno} - {self.valor_mensal}"


class FinancialEntry(models.Model):
    TIPOS = [("income", "Income"), ("expense", "Expense")]
    descricao = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="lancamentos_financeiros")

    class Meta:
        ordering = ["-data", "-id"]

    def __str__(self):
        return f"{self.descricao} ({self.tipo})"