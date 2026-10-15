from django.contrib.auth.models import User
from django.db import models

from academico.models import Nivel


class Competencia(models.Model):
    nome = models.CharField(max_length=100)
    ativa = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "accounts_competencia"
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
        db_table = "accounts_avaliacao"
        ordering = ["-data"]

    def __str__(self):
        return f"Evaluation of {self.aluno} on {self.data}"


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

    class Meta:
        db_table = "accounts_notacompetencia"

    def __str__(self):
        return f"{self.competencia.nome} - {self.nivel}"
