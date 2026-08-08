from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Perfil

@receiver(post_save, sender=User)
def criar_perfil(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(
            user=instance,
            deve_trocar_senha=not (instance.is_staff or instance.is_superuser),
        )

@receiver(post_save, sender=User)
def salvar_perfil(sender, instance, created, **kwargs):
    if created:
        return
    try:
        instance.perfil.save()
    except Perfil.DoesNotExist:
        Perfil.objects.create(user=instance)