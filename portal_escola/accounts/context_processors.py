from .permissions import is_professor, is_aluno


def user_roles(request):
    return {
        "is_professor": is_professor(request.user),
        "is_aluno": is_aluno(request.user),
    }
