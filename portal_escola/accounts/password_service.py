import secrets

from django.urls import reverse

from .email_utils import enviar_senha_provisoria
from .models import Perfil


def redefinir_senha_e_enviar_email(user, request=None):
    """
    Define senha provisória, marca perfil.deve_trocar_senha e envia e-mail.
    Retorna (sucesso_envio: bool, mensagem_erro: str|None).
    """
    nova_senha = secrets.token_urlsafe(8)
    user.set_password(nova_senha)
    user.save()

    perfil, _ = Perfil.objects.get_or_create(user=user)
    perfil.deve_trocar_senha = True
    perfil.save(update_fields=["deve_trocar_senha"])

    user.refresh_from_db()

    login_url = None
    if request is not None:
        login_url = request.build_absolute_uri(reverse("login"))

    destinatario = (user.email or "").strip() or (user.username or "").strip()
    nome = user.get_full_name() or user.first_name or ""
    return enviar_senha_provisoria(
        destinatario,
        nova_senha,
        nome=nome,
        login_url=login_url,
    )
