from django.shortcuts import get_object_or_404,render, redirect
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User, Group
from .models import Turma, Aula, Presenca, Aluno, Professor, Avaliacao
from datetime import date
from .forms import AlunoForm, ProfessorForm, LoginForm
from accounts.models import Perfil



from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .permissions import is_professor, is_aluno, professor_required, is_diretor, diretor_required

class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    authentication_form = LoginForm

    def get_success_url(self):
        user = self.request.user

        if is_professor(user):
            return reverse_lazy("dashboard")

        if is_aluno(user):
            return reverse_lazy("feed")

        return reverse_lazy("dashboard")  # <- nunca volte para login


@login_required
def trocar_senha(request):
    if request.method == "POST":
        nova_senha = request.POST.get("nova_senha")

        user = request.user
        user.set_password(nova_senha)
        user.save()

        user.perfil.deve_trocar_senha = False
        user.perfil.save()

        return redirect("login")

    return render(request, "trocar_senha.html")

from django.contrib.auth.models import User
import secrets

@login_required
def resetar_senha(request, user_id):

    if not (
        request.user.groups.filter(name="Professores").exists()
        or request.user.groups.filter(name="Diretoria").exists()
    ):
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":

        nova_senha = secrets.token_urlsafe(8)
        user.set_password(nova_senha)
        user.save()

        perfil, created = Perfil.objects.get_or_create(user=user)
        perfil.deve_trocar_senha = True
        perfil.save()

        send_mail(
            "Nova senha provisória",
            f"Sua nova senha é: {nova_senha}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )

        messages.success(
            request,
            f"Senha redefinida com sucesso. Um e-mail foi enviado para {user.email}"
        )

        return redirect("lista_alunos")

    # Se alguém tentar acessar via GET direto
    return redirect("lista_alunos")

def resetar_senha_professor(request, user_id):

    if not (
        request.user.groups.filter(name="Diretoria").exists()
    ):
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":

        nova_senha = secrets.token_urlsafe(8)
        user.set_password(nova_senha)
        user.save()

        perfil, created = Perfil.objects.get_or_create(user=user)
        perfil.deve_trocar_senha = True
        perfil.save()

        send_mail(
            "Nova senha provisória",
            f"Sua nova senha é: {nova_senha}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )

        messages.success(
            request,
            f"Senha redefinida com sucesso. Um e-mail foi enviado para {user.email}"
        )

        return redirect("lista_professores")

    # Se alguém tentar acessar via GET direto
    return redirect("lista_professores")

User = get_user_model()

@login_required
def dashboard(request):

    grupo_alunos = Group.objects.filter(name="Alunos").first()
    grupo_professores = Group.objects.filter(name="Professores").first()

    total_alunos = grupo_alunos.user_set.count() if grupo_alunos else 0
    total_professores = grupo_professores.user_set.count() if grupo_professores else 0

    context = {
        'total_alunos': total_alunos,
        'total_professores': total_professores,
        'total_turmas': Turma.objects.count(),
        'total_avaliacoes': Avaliacao.objects.count(),
    }

    return render(request, 'accounts/dashboard.html', context)


from django.shortcuts import get_object_or_404, render, redirect
from datetime import date
from .models import Turma, Aula, Presenca

from accounts.permissions import professor_required

@professor_required
def marcar_presenca(request, turma_id):
    turma = get_object_or_404(Turma, id=turma_id)

    # Cria ou recupera a aula de hoje
    aula, criada = Aula.objects.get_or_create(
        turma=turma,
        data=date.today(),
        defaults={'professor': request.user}
    )

    alunos = turma.alunos.all()

    if request.method == "POST":
        for aluno in alunos:
            presente = request.POST.get(f"aluno_{aluno.id}") == "on"

            Presenca.objects.update_or_create(
                aula=aula,
                aluno=aluno,
                defaults={"presente": presente}
            )

        return redirect("dashboard")

    return render(request, "accounts/marcar_presenca.html", {
        "turma": turma,
        "alunos": alunos,
    })


from django.shortcuts import render


def feed(request):

    return render(request, "accounts/feed.html")


from .forms import AvaliacaoForm
from .models import Avaliacao, NotaCompetencia, Competencia

@login_required
def nova_avaliacao(request):
    if request.method == "POST":
        form = AvaliacaoForm(request.POST)
        if form.is_valid():
            aluno = form.cleaned_data["aluno"]
            observacoes = form.cleaned_data["observacoes"]

            avaliacao = Avaliacao.objects.create(
                aluno=aluno,
                professor=request.user,
                observacoes=observacoes
            )

            competencias = Competencia.objects.filter(ativa=True)

            for competencia in competencias:
                nivel = form.cleaned_data[f"competencia_{competencia.id}"]

                NotaCompetencia.objects.create(
                    avaliacao=avaliacao,
                    competencia=competencia,
                    nivel=nivel
                )

            return redirect("dashboard")

    else:
        form = AvaliacaoForm()

    return render(request, "accounts/nova_avaliacao.html", {"form": form})

@login_required
@diretor_required
def lista_professores(request):
    busca = request.GET.get("q")

    professores = User.objects.filter(groups__name="Professores")

    if not is_diretor(request.user):
        professores = professores.filter(is_active=True)

    if busca:
        professores = professores.filter(first_name__icontains=busca)

    context = {
        "professores": professores,
        "busca": busca
    }

    return render(request, "accounts/lista_professores.html", context)

@login_required
def lista_alunos(request):
    busca = request.GET.get("q")

    alunos = User.objects.filter(groups__name="Alunos")

    if not is_diretor(request.user):
        alunos = alunos.filter(is_active=True)

    if busca:
        alunos = alunos.filter(first_name__icontains=busca)

    context = {
        "alunos": alunos,
        "busca": busca
    }

    return render(request, "accounts/lista_alunos.html", context)

@login_required
def detalhe_aluno(request, id):
    aluno = get_object_or_404(Aluno, user__id=id)

    if request.method == "POST":
        form = AlunoForm(request.POST, instance=aluno)
        if form.is_valid():
            form.save()
            return redirect("detalhe_aluno", id=id)
    else:
        form = AlunoForm(instance=aluno)

    return render(request, "accounts/detalhe_aluno.html", {
        "aluno": aluno,
        "form": form
    })

@login_required
@diretor_required
def detalhe_professor(request, id):
    professor = get_object_or_404(Professor, user__id=id)

    if request.method == "POST":
        form = ProfessorForm(request.POST, instance=professor)
        if form.is_valid():
            form.save()
            return redirect("detalhe_professor", id=id)
    else:
        form = ProfessorForm(instance=professor)

    return render(request, "accounts/detalhe_professor.html", {
        "professor": professor,
        "form": form
    })

import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from .models import Perfil

def criar_aluno(request):
    if request.method == "POST":
        form = AlunoForm(request.POST)

        if form.is_valid():
            nome = form.cleaned_data['nome']
            sobrenome = form.cleaned_data['sobrenome']
            email = form.cleaned_data['email']

            senha_temporaria = secrets.token_urlsafe(8)

            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=nome,
                last_name=sobrenome,
                password=senha_temporaria
            )

            aluno = form.save(commit=False)
            aluno.user = user   # 🔥 VINCULA O USER AQUI
            aluno.save()

            user.perfil.deve_trocar_senha = True
            user.perfil.save()

            grupo = Group.objects.get(name="Alunos")
            user.groups.add(grupo)

            return redirect("lista_alunos")
    else:
        form = AlunoForm()

    return render(request, "accounts/criar_aluno.html", {"form": form})


@login_required
def desativar_aluno(request, user_id):
    aluno = User.objects.get(id=user_id)
    aluno.is_active = False
    aluno.save()
    return redirect("lista_alunos")

from django.http import HttpResponseForbidden
from .permissions import is_diretor

@login_required
def reativar_aluno(request, user_id):
    if not is_diretor(request.user):
        return HttpResponseForbidden()

    aluno = User.objects.get(id=user_id)
    aluno.is_active = True
    aluno.save()
    return redirect("lista_alunos")


def criar_professor(request):
    if request.method == "POST":
        form = ProfessorForm(request.POST)

        if form.is_valid():
            nome = form.cleaned_data['nome']
            sobrenome = form.cleaned_data['sobrenome']
            email = form.cleaned_data['email']

            senha_temporaria = secrets.token_urlsafe(8)

            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=nome,
                last_name=sobrenome,
                password=senha_temporaria
            )

            professor = form.save(commit=False)
            professor.user = user   # 🔥 VINCULA O USER AQUI
            professor.save()

            user.perfil.deve_trocar_senha = True
            user.perfil.save()

            grupo = Group.objects.get(name="Professores")
            user.groups.add(grupo)

            return redirect("lista_professores")
    else:
        form = ProfessorForm()

    return render(request, "accounts/criar_professor.html", {"form": form})

@login_required
@diretor_required
def desativar_professor(request, user_id):
    professor = User.objects.get(id=user_id)
    professor.is_active = False
    professor.save()
    return redirect("lista_professores")

@login_required
def reativar_professor(request, user_id):
    if not is_diretor(request.user):
        return HttpResponseForbidden()

    professor = User.objects.get(id=user_id)
    professor.is_active = True
    professor.save()
    return redirect("lista_professores")