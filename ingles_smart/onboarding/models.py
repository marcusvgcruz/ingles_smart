from django.contrib.auth.models import User
from django.db import models

from academico.models import Aluno


class OnboardingItem(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "accounts_onboardingitem"
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
        db_table = "accounts_onboardingalunoitem"
        unique_together = ("aluno", "item")
        ordering = ["item__ordem", "item__nome"]

    def __str__(self):
        return f"{self.aluno} - {self.item.nome}"
