from django.contrib.auth.decorators import user_passes_test

def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

def is_diretor(user):
    return user.groups.filter(name="Diretoria").exists()


def is_professor(user):
    return user.is_authenticated and user.groups.filter(name="Professores").exists()


def is_aluno(user):
    return user.is_authenticated and user.groups.filter(name="Alunos").exists()


def deve_forcar_troca_senha(user):
    """Troca obrigatória só para alunos/professores com senha provisória (não staff/admin)."""
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return False
    perfil = getattr(user, "perfil", None)
    return bool(perfil and perfil.deve_trocar_senha)


def is_administração(user):
    return user.is_authenticated and user.groups.filter(name="Administrativo").exists()

from django.http import HttpResponseForbidden
from functools import wraps

def diretor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_diretor(request.user):
            return HttpResponseForbidden("Acesso restrito à diretoria.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def professor_required(view_func):
    decorated_view = user_passes_test(is_professor)(view_func)
    return decorated_view


def aluno_required(view_func):
    decorated_view = user_passes_test(is_aluno)(view_func)
    return decorated_view


def administrativo_required(view_func):
    decorated_view = user_passes_test(is_administração)(view_func)
    return decorated_view

