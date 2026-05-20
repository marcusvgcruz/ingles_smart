import logging
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

logger = logging.getLogger(__name__)

_BACKENDS_SEM_ENTREGA = (
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
)


def email_entrega_real_configurado():
    backend = settings.EMAIL_BACKEND or ""
    return not any(b in backend for b in _BACKENDS_SEM_ENTREGA)


def validar_configuracao_email():
    if not email_entrega_real_configurado():
        return (
            False,
            "SMTP não configurado: o servidor está usando backend de desenvolvimento "
            f"({settings.EMAIL_BACKEND}). Crie o arquivo .env com as variáveis de e-mail "
            "e reinicie o runserver.",
        )
    if not settings.EMAIL_HOST:
        return False, "EMAIL_HOST não configurado."
    if not settings.EMAIL_HOST_USER:
        return False, "EMAIL_HOST_USER não configurado."
    if not settings.EMAIL_HOST_PASSWORD:
        return False, "EMAIL_HOST_PASSWORD não configurado."
    return True, None


def _registrar_log_arquivo(destinatario, sucesso, detalhe=""):
    try:
        log_dir = Path(settings.BASE_DIR) / "logs"
        log_dir.mkdir(exist_ok=True)
        linha = (
            f"backend={settings.EMAIL_BACKEND} | to={destinatario} | "
            f"ok={sucesso} | {detalhe}\n"
        )
        (log_dir / "email.log").open("a", encoding="utf-8").write(linha)
    except OSError:
        logger.debug("Não foi possível gravar logs/email.log", exc_info=True)


def _remetente_efetivo():
    """Gmail/Outlook exigem que o remetente coincida com a conta SMTP autenticada."""
    if settings.EMAIL_HOST_USER and "@" in settings.EMAIL_HOST_USER:
        return settings.EMAIL_HOST_USER
    return settings.DEFAULT_FROM_EMAIL


def enviar_senha_provisoria(destinatario, senha, nome=None, login_url=None):
    """
    Envia e-mail com senha provisória. Retorna (sucesso: bool, mensagem_erro: str|None).
    """
    destinatario = (destinatario or "").strip()
    if not destinatario:
        return False, "Usuário sem e-mail cadastrado."
    if "@" not in destinatario:
        return False, f"Endereço inválido no cadastro: {destinatario!r}"

    ok_config, erro_config = validar_configuracao_email()
    if not ok_config:
        logger.error("Configuração de e-mail inválida: %s", erro_config)
        _registrar_log_arquivo(destinatario, False, erro_config)
        return False, erro_config

    nome_exibicao = (nome or "").strip() or destinatario
    escola = getattr(settings, "SCHOOL_DISPLAY_NAME", "Inglês Smart")
    portal_url = login_url or getattr(settings, "PORTAL_LOGIN_URL", "")
    remetente = _remetente_efetivo()

    assunto = f"Sua senha provisoria - {escola}"
    linhas = [
        f"Ola, {nome_exibicao}!",
        "",
        "Sua senha provisoria para acessar o portal:",
        "",
        senha,
        "",
        "No primeiro acesso voce devera cadastrar uma senha pessoal.",
    ]
    if portal_url:
        linhas.extend(["", f"Acesse o portal: {portal_url}"])
    linhas.extend(["", f"Atenciosamente,", f"Equipe {escola}"])

    corpo = "\n".join(linhas)

    try:
        conexao = get_connection(
            backend=settings.EMAIL_BACKEND,
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER or None,
            password=settings.EMAIL_HOST_PASSWORD or None,
            use_tls=settings.EMAIL_USE_TLS,
            use_ssl=settings.EMAIL_USE_SSL,
            fail_silently=False,
        )
        mensagem = EmailMessage(
            subject=assunto,
            body=corpo,
            from_email=remetente,
            to=[destinatario],
            connection=conexao,
        )
        enviados = mensagem.send(fail_silently=False)
        if enviados < 1:
            msg = "O servidor SMTP não confirmou o envio."
            _registrar_log_arquivo(destinatario, False, msg)
            return False, msg

        detalhe = f"from={remetente} | enviados={enviados}"
        logger.info("Senha provisoria enviada para %s (%s)", destinatario, detalhe)
        _registrar_log_arquivo(destinatario, True, detalhe)
        return True, None
    except Exception as exc:
        logger.exception("Falha ao enviar senha provisoria para %s", destinatario)
        _registrar_log_arquivo(destinatario, False, str(exc))
        return False, str(exc)
