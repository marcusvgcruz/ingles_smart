import json
import logging
import socket
import urllib.error
import urllib.request
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

_RENDER_SMTP_HINT = (
    "Could not connect to the mail server (timeout). "
    "On Render's free plan, SMTP ports 587/465 are blocked — configure BREVO_API_KEY "
    "in the Render dashboard (see .env.example) or upgrade to a paid web service."
)


def _usa_brevo():
    return bool(getattr(settings, "BREVO_API_KEY", ""))


def _usa_resend():
    return bool(getattr(settings, "RESEND_API_KEY", ""))


def _backend_log_label():
    if _usa_brevo():
        return "brevo"
    if _usa_resend():
        return "resend"
    return settings.EMAIL_BACKEND


def email_entrega_real_configurado():
    if _usa_brevo() or _usa_resend():
        return True
    backend = settings.EMAIL_BACKEND or ""
    return not any(b in backend for b in _BACKENDS_SEM_ENTREGA)


def validar_configuracao_email():
    if _usa_brevo():
        remetente = _remetente_efetivo()
        if not remetente or "@" not in remetente:
            return (
                False,
                "BREVO_API_KEY is set but BREVO_FROM_EMAIL (or DEFAULT_FROM_EMAIL) "
                "must be the verified sender address in Brevo.",
            )
        return True, None

    if _usa_resend():
        remetente = _remetente_efetivo()
        if not remetente or "@" not in remetente:
            return (
                False,
                "RESEND_API_KEY is set but DEFAULT_FROM_EMAIL (or RESEND_FROM_EMAIL) "
                "must be a verified sender address in Resend.",
            )
        return True, None

    if not email_entrega_real_configurado():
        return (
            False,
            "SMTP not configured: the server is using a development backend "
            f"({settings.EMAIL_BACKEND}). Create the .env file with email variables "
            "and restart the server.",
        )
    if not settings.EMAIL_HOST:
        return False, "EMAIL_HOST is not configured."
    if not settings.EMAIL_HOST_USER:
        return False, "EMAIL_HOST_USER is not configured."
    if not settings.EMAIL_HOST_PASSWORD:
        return False, "EMAIL_HOST_PASSWORD is not configured."
    return True, None


def _registrar_log_arquivo(destinatario, sucesso, detalhe=""):
    try:
        log_dir = Path(settings.BASE_DIR) / "logs"
        log_dir.mkdir(exist_ok=True)
        linha = (
            f"backend={_backend_log_label()} | to={destinatario} | "
            f"ok={sucesso} | {detalhe}\n"
        )
        (log_dir / "email.log").open("a", encoding="utf-8").write(linha)
    except OSError:
        logger.debug("Não foi possível gravar logs/email.log", exc_info=True)


def _remetente_efetivo():
    if _usa_brevo():
        return getattr(settings, "BREVO_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL
    if _usa_resend():
        return getattr(settings, "RESEND_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL

    # Gmail/Outlook exigem que o remetente coincida com a conta SMTP autenticada.
    if settings.EMAIL_HOST_USER and "@" in settings.EMAIL_HOST_USER:
        return settings.EMAIL_HOST_USER
    return settings.DEFAULT_FROM_EMAIL


def _nome_remetente():
    return (
        getattr(settings, "BREVO_FROM_NAME", "").strip()
        or getattr(settings, "SCHOOL_DISPLAY_NAME", "Inglês Smart")
    )


def _mensagem_erro_envio(exc):
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return _RENDER_SMTP_HINT
    msg = str(exc).lower()
    if "timed out" in msg or "timeout" in msg:
        return _RENDER_SMTP_HINT
    return str(exc)


def _enviar_via_brevo(remetente, destinatario, assunto, corpo):
    payload = json.dumps(
        {
            "sender": {"name": _nome_remetente(), "email": remetente},
            "to": [{"email": destinatario}],
            "subject": assunto,
            "textContent": corpo,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "api-key": settings.BREVO_API_KEY,
            "Content-Type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    timeout = getattr(settings, "EMAIL_TIMEOUT", 10)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        if response.status not in (200, 201):
            raise RuntimeError(f"Brevo API error ({response.status}): {body}")
    return body


def _enviar_via_resend(remetente, destinatario, assunto, corpo):
    payload = json.dumps(
        {
            "from": remetente,
            "to": [destinatario],
            "subject": assunto,
            "text": corpo,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    timeout = getattr(settings, "EMAIL_TIMEOUT", 10)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        if response.status not in (200, 201):
            raise RuntimeError(f"Resend API error ({response.status}): {body}")
    return body


def enviar_senha_provisoria(destinatario, senha, nome=None, login_url=None):
    """
    Envia e-mail com senha provisória. Retorna (sucesso: bool, mensagem_erro: str|None).
    """
    destinatario = (destinatario or "").strip()
    if not destinatario:
        return False, "User has no registered email."
    if "@" not in destinatario:
        return False, f"Invalid address on file: {destinatario!r}"

    ok_config, erro_config = validar_configuracao_email()
    if not ok_config:
        logger.error("Configuração de e-mail inválida: %s", erro_config)
        _registrar_log_arquivo(destinatario, False, erro_config)
        return False, erro_config

    nome_exibicao = (nome or "").strip() or destinatario
    escola = getattr(settings, "SCHOOL_DISPLAY_NAME", "Inglês Smart")
    portal_url = login_url or getattr(settings, "PORTAL_LOGIN_URL", "")
    remetente = _remetente_efetivo()

    assunto = f"Your temporary password - {escola}"
    linhas = [
        f"Hello, {nome_exibicao}!",
        "",
        "Your temporary password to access the portal:",
        "",
        senha,
        "",
        "On your first login you must set a personal password.",
    ]
    if portal_url:
        linhas.extend(["", f"Access the portal: {portal_url}"])
    linhas.extend(["", "Best regards,", f"{escola} team"])

    corpo = "\n".join(linhas)

    try:
        if _usa_brevo():
            resposta = _enviar_via_brevo(remetente, destinatario, assunto, corpo)
            detalhe = f"from={remetente} | brevo={resposta}"
            logger.info("Senha provisoria enviada via Brevo para %s (%s)", destinatario, detalhe)
            _registrar_log_arquivo(destinatario, True, detalhe)
            return True, None

        if _usa_resend():
            resposta = _enviar_via_resend(remetente, destinatario, assunto, corpo)
            detalhe = f"from={remetente} | resend={resposta}"
            logger.info("Senha provisoria enviada via Resend para %s (%s)", destinatario, detalhe)
            _registrar_log_arquivo(destinatario, True, detalhe)
            return True, None

        conexao = get_connection(
            backend=settings.EMAIL_BACKEND,
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER or None,
            password=settings.EMAIL_HOST_PASSWORD or None,
            use_tls=settings.EMAIL_USE_TLS,
            use_ssl=settings.EMAIL_USE_SSL,
            timeout=getattr(settings, "EMAIL_TIMEOUT", 10),
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
            msg = "The SMTP server did not confirm delivery."
            _registrar_log_arquivo(destinatario, False, msg)
            return False, msg

        detalhe = f"from={remetente} | enviados={enviados}"
        logger.info("Senha provisoria enviada para %s (%s)", destinatario, detalhe)
        _registrar_log_arquivo(destinatario, True, detalhe)
        return True, None
    except urllib.error.HTTPError as exc:
        erro_body = exc.read().decode("utf-8", errors="replace")
        provedor = "Brevo" if _usa_brevo() else "Resend"
        msg = f"{provedor} API error ({exc.code}): {erro_body}"
        logger.exception("Falha ao enviar senha provisoria via %s para %s", provedor, destinatario)
        _registrar_log_arquivo(destinatario, False, msg)
        return False, msg
    except Exception as exc:
        msg = _mensagem_erro_envio(exc)
        logger.exception("Falha ao enviar senha provisoria para %s", destinatario)
        _registrar_log_arquivo(destinatario, False, msg)
        return False, msg
