from .permissions import is_professor, is_aluno
from .models import Perfil


def user_roles(request):
    perfil = None
    if request.user.is_authenticated:
        try:
            perfil = request.user.perfil
        except Perfil.DoesNotExist:
            perfil = None
    return {
        "is_professor": is_professor(request.user),
        "is_aluno": is_aluno(request.user),
        "user_perfil": perfil,
    }
