from django.contrib.auth.models import User
from django.db import models

from academico.models import Aluno


class Contract(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="contratos")
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    inicio = models.DateField()
    fim = models.DateField(null=True, blank=True)
    observacao = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "accounts_contract"
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
        db_table = "accounts_financialentry"
        ordering = ["-data", "-id"]

    def __str__(self):
        return f"{self.descricao} ({self.tipo})"
