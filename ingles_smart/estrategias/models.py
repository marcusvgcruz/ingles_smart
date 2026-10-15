from django.contrib.auth.models import User
from django.db import models

from accounts.storage import raw_file_storage
from academico.models import Aluno


class Estrategia(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    pdf_portugues = models.FileField(
        upload_to="estrategias/pdf/", storage=raw_file_storage, null=True, blank=True
    )
    pdf_ingles = models.FileField(
        upload_to="estrategias/pdf/", storage=raw_file_storage, null=True, blank=True
    )
    study_sesh_portuguese = models.FileField(
        upload_to="estrategias/audio/", storage=raw_file_storage, null=True, blank=True
    )
    study_sesh_english = models.FileField(
        upload_to="estrategias/audio/", storage=raw_file_storage, null=True, blank=True
    )
    strategy_portuguese = models.FileField(
        upload_to="estrategias/audio/", storage=raw_file_storage, null=True, blank=True
    )
    strategy_brazilian_english = models.FileField(
        upload_to="estrategias/audio/", storage=raw_file_storage, null=True, blank=True
    )
    strategy_irish_english = models.FileField(
        upload_to="estrategias/audio/", storage=raw_file_storage, null=True, blank=True
    )
    strategy_australian_english = models.FileField(
        upload_to="estrategias/audio/", storage=raw_file_storage, null=True, blank=True
    )

    class Meta:
        db_table = "accounts_estrategia"
        ordering = ["numero"]
        verbose_name_plural = "Strategies"

    def __str__(self):
        return self.titulo

    def audio_field_labels(self):
        n = self.numero
        return [
            ("study_sesh_portuguese", f"Study Sesh {n} - portuguese"),
            ("study_sesh_english", f"Study Sesh {n} - English"),
            ("strategy_portuguese", f"Strategy {n} (Portuguese)"),
            ("strategy_brazilian_english", f"Strategy {n} (Brazilian english)"),
            ("strategy_irish_english", f"Strategy {n} (Irish English)"),
            ("strategy_australian_english", f"Strategy {n} (Australian English)"),
        ]

    def audio_items(self):
        items = []
        for field_name, label in self.audio_field_labels():
            audio_file = getattr(self, field_name)
            if audio_file:
                items.append({"label": label, "url": audio_file.url})
        return items

    def has_any_audio(self):
        return any(getattr(self, name) for name, _ in self.audio_field_labels())


class EstrategiaAlunoAcesso(models.Model):
    estrategia = models.ForeignKey(Estrategia, on_delete=models.CASCADE, related_name="acessos")
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="estrategias_acesso")
    liberado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="estrategias_liberadas",
    )
    liberado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_estrategiaalunoacesso"
        unique_together = ("estrategia", "aluno")
        ordering = ["aluno__user__first_name", "aluno__user__last_name"]

    def __str__(self):
        return f"{self.aluno} — {self.estrategia}"
