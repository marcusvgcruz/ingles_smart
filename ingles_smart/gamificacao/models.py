from django.contrib.auth.models import User
from django.db import models

from accounts.storage import raw_file_storage
from academico.models import Aluno


class GamificationChallenge(models.Model):
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    pontos = models.PositiveIntegerField(default=10)
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="desafios_criados")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_gamificationchallenge"
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
        db_table = "accounts_gamificationsubmission"
        unique_together = ("challenge", "aluno")
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.aluno} - {self.challenge}"


class GamificationChallengeMedia(models.Model):
    challenge = models.ForeignKey(GamificationChallenge, on_delete=models.CASCADE, related_name="midias")
    imagem = models.ImageField(upload_to="gamification/challenges/images/", null=True, blank=True)
    arquivo = models.FileField(
        upload_to="gamification/challenges/files/",
        storage=raw_file_storage,
        null=True,
        blank=True,
    )
    video_url = models.URLField(blank=True, null=True)

    class Meta:
        db_table = "accounts_gamificationchallengemedia"


class GamificationSubmissionMedia(models.Model):
    submission = models.ForeignKey(GamificationSubmission, on_delete=models.CASCADE, related_name="midias")
    imagem = models.ImageField(upload_to="gamification/submissions/images/", null=True, blank=True)
    arquivo = models.FileField(
        upload_to="gamification/submissions/files/",
        storage=raw_file_storage,
        null=True,
        blank=True,
    )
    video_url = models.URLField(blank=True, null=True)

    class Meta:
        db_table = "accounts_gamificationsubmissionmedia"
