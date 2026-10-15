from django.contrib.auth.models import User
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from accounts.storage import raw_file_storage
from academico.models import Aluno


class Post(models.Model):
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    conteudo = CKEditor5Field(blank=True, config_name="default")
    criado_em = models.DateTimeField(auto_now_add=True)
    is_fixo = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_post"

    def __str__(self):
        return f"{self.autor} - {self.criado_em}"


class PostImagem(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='imagens')
    imagem = models.ImageField(upload_to='feed/imagens/')

    class Meta:
        db_table = "accounts_postimagem"


class PostArquivo(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='arquivos')
    arquivo = models.FileField(upload_to='feed/arquivos/', storage=raw_file_storage)
    nome = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "accounts_postarquivo"

    def save(self, *args, **kwargs):
        if not self.nome and self.arquivo:
            import os

            self.nome = os.path.basename(self.arquivo.name or "file")[:255]
        super().save(*args, **kwargs)

class TarefaAluno(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='tarefas')

    nome = models.CharField(max_length=255)
    concluido = models.BooleanField(default=False)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_tarefaaluno"
