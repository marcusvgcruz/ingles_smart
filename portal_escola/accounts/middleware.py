from django.shortcuts import redirect
from django.urls import reverse

from .permissions import deve_forcar_troca_senha


class MustChangePasswordMiddleware:
    """Redireciona usuários com senha provisória para troca obrigatória."""

    EXEMPT_URL_NAMES = frozenset({
        "trocar_senha",
        "logout",
        "login",
        "esqueci_senha",
    })

    # resolver_match ainda não existe nesta fase do middleware — usar path também.
    EXEMPT_PATHS = frozenset({
        "/login",
        "/logout",
        "/trocar-senha",
        "/esqueci-senha",
    })

    def __init__(self, get_response):
        self.get_response = get_response

    def _request_is_exempt(self, request):
        if request.path.startswith("/static/") or request.path.startswith("/media/"):
            return True

        path = request.path.rstrip("/") or "/"
        if path in self.EXEMPT_PATHS:
            return True

        resolver = getattr(request, "resolver_match", None)
        if resolver and resolver.url_name in self.EXEMPT_URL_NAMES:
            return True

        return False

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and deve_forcar_troca_senha(request.user)
            and not self._request_is_exempt(request)
        ):
            return redirect(reverse("trocar_senha"))

        return self.get_response(request)
