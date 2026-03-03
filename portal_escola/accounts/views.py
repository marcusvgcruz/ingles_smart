from datetime import date
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from .forms import AlunoForm, AvaliacaoForm, ProfessorForm, TurmaForm
from .models import (
    Aluno,
    Aula,
    Avaliacao,
    Competencia,
    NotaCompetencia,
    Perfil,
    Presenca,
    Professor,
    Turma,
    TurmaHorario,
    TurmaHorarioAluno,
)
from .permissions import (
    diretor_required,
    is_aluno,
    is_diretor,
    is_professor,
    professor_required,
)


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if is_professor(user):
            return reverse_lazy("dashboard")
        if is_aluno(user):
            return reverse_lazy("feed")
        return reverse_lazy("dashboard")


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

    return render(request, "accounts/trocar_senha.html")


@login_required
def resetar_senha(request, user_id):
    if not (is_professor(request.user) or is_diretor(request.user)):
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        nova_senha = secrets.token_urlsafe(8)
        user.set_password(nova_senha)
        user.save()

        perfil, _ = Perfil.objects.get_or_create(user=user)
        perfil.deve_trocar_senha = True
        perfil.save()

        send_mail(
            "Nova senha provisória",
            f"Sua nova senha é: {nova_senha}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )

        messages.success(request, f"Senha redefinida com sucesso. Um e-mail foi enviado para {user.email}")
        return redirect("lista_alunos")

    return redirect("lista_alunos")


@login_required
def resetar_senha_professor(request, user_id):
    if not is_diretor(request.user):
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        nova_senha = secrets.token_urlsafe(8)
        user.set_password(nova_senha)
        user.save()

        perfil, _ = Perfil.objects.get_or_create(user=user)
        perfil.deve_trocar_senha = True
        perfil.save()

        send_mail(
            "Nova senha provisória",
            f"Sua nova senha é: {nova_senha}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )

        messages.success(request, f"Senha redefinida com sucesso. Um e-mail foi enviado para {user.email}")
        return redirect("lista_professores")

    return redirect("lista_professores")


User = get_user_model()


@login_required
def dashboard(request):
    grupo_alunos = Group.objects.filter(name="Alunos").first()
    grupo_professores = Group.objects.filter(name="Professores").first()

    total_alunos = grupo_alunos.user_set.count() if grupo_alunos else 0
    total_professores = grupo_professores.user_set.count() if grupo_professores else 0

    context = {
        "total_alunos": total_alunos,
        "total_professores": total_professores,
        "total_turmas": Turma.objects.count(),
        "total_avaliacoes": Avaliacao.objects.count(),
    }
    return render(request, "accounts/dashboard.html", context)


def _pode_gerenciar_turma(user):
    return is_professor(user) or is_diretor(user)


@login_required
def lista_turmas(request):
    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden("Apenas professores e diretoria podem gerenciar turmas.")

    turmas = (
        Turma.objects.prefetch_related("horarios__vinculos__aluno")
        .all()
        .order_by("nome")
    )

    return render(request, "accounts/lista_turmas.html", {"turmas": turmas})


@login_required
def criar_turma(request):
    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden("Apenas professores e diretoria podem criar turmas.")

    form = TurmaForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        turma = form.save()
        dias = form.cleaned_data["dias_semana"]
        horario = form.cleaned_data["horario"]

        TurmaHorario.objects.bulk_create(
            [TurmaHorario(turma=turma, dia_semana=dia, horario=horario) for dia in dias]
        )
        messages.success(request, "Turma criada com sucesso.")
        return redirect("lista_turmas")

    return render(request, "accounts/form_turma.html", {"form": form, "titulo": "Nova turma"})


@login_required
def editar_turma(request, turma_id):
    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden("Apenas professores e diretoria podem editar turmas.")

    turma = get_object_or_404(Turma, id=turma_id)
    horarios = turma.horarios.all()

    initial = {}
    if horarios.exists():
        initial = {
            "dias_semana": [h.dia_semana for h in horarios],
            "horario": horarios.first().horario,
        }

    form = TurmaForm(request.POST or None, instance=turma, initial=initial)

    if request.method == "POST" and form.is_valid():
        turma = form.save()
        dias = form.cleaned_data["dias_semana"]
        horario = form.cleaned_data["horario"]

        TurmaHorario.objects.filter(turma=turma).delete()
        TurmaHorario.objects.bulk_create(
            [TurmaHorario(turma=turma, dia_semana=dia, horario=horario) for dia in dias]
        )

        messages.success(request, "Turma atualizada com sucesso.")
        return redirect("lista_turmas")

    return render(request, "accounts/form_turma.html", {"form": form, "titulo": "Editar turma", "turma": turma})


@login_required
def vinculo_manual_turma(request, turma_id):
    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden("Apenas professores e diretoria podem vincular alunos.")

    turma = get_object_or_404(Turma, id=turma_id)
    horarios = turma.horarios.all().order_by("dia_semana")
    alunos = User.objects.filter(groups__name="Alunos", is_active=True).order_by("first_name", "last_name")

    if request.method == "POST":
        aluno_id = request.POST.get("aluno_id")
        horarios_ids = request.POST.getlist("horarios")

        if not aluno_id or not horarios_ids:
            messages.error(request, "Selecione um aluno e ao menos um horário para vincular.")
            return redirect("vinculo_manual_turma", turma_id=turma.id)

        aluno = get_object_or_404(User, id=aluno_id)
        for horario_id in horarios_ids:
            horario = get_object_or_404(TurmaHorario, id=horario_id, turma=turma)
            TurmaHorarioAluno.objects.get_or_create(turma_horario=horario, aluno=aluno)

        messages.success(request, "Vínculo criado com sucesso.")
        return redirect("lista_turmas")

    return render(
        request,
        "accounts/vinculo_manual_turma.html",
        {"turma": turma, "horarios": horarios, "alunos": alunos},
    )


@login_required
def remover_vinculo_turma(request, vinculo_id):
    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden("Apenas professores e diretoria podem remover vínculos.")

    vinculo = get_object_or_404(TurmaHorarioAluno, id=vinculo_id)
    turma_id = vinculo.turma_horario.turma.id
    vinculo.delete()
    messages.success(request, "Vínculo removido apenas deste horário.")
    return redirect("lista_turmas")


@professor_required
def marcar_presenca(request, turma_horario_id):
    turma_horario = get_object_or_404(TurmaHorario, id=turma_horario_id)

    aula, _ = Aula.objects.get_or_create(turma_horario=turma_horario, data=date.today())

    if aula.professor is None:
        aula.professor = request.user
        aula.save(update_fields=["professor"])

    vinculos = turma_horario.vinculos.select_related("aluno").all()

    if request.method == "POST":
        for vinculo in vinculos:
            presente = request.POST.get(f"aluno_{vinculo.aluno.id}") == "on"
            Presenca.objects.update_or_create(
                aula=aula,
                aluno=vinculo.aluno,
                defaults={"presente": presente},
            )

        messages.success(request, "Presença registrada com sucesso.")
        return redirect("lista_turmas")

    return render(
        request,
        "accounts/marcar_presenca.html",
        {"turma_horario": turma_horario, "vinculos": vinculos},
    )


@login_required
def feed(request):
    return render(request, "accounts/feed.html")


@login_required
def nova_avaliacao(request):
    aluno_id = request.GET.get("aluno")

    if request.method == "POST":
        form = AvaliacaoForm(request.POST)
        if form.is_valid():
            aluno = form.cleaned_data["aluno"]
            observacoes = form.cleaned_data["observacoes"]

            avaliacao = Avaliacao.objects.create(
                aluno=aluno,
                professor=request.user,
                observacoes=observacoes,
            )

            competencias = Competencia.objects.filter(ativa=True)
            for competencia in competencias:
                nivel = form.cleaned_data[f"competencia_{competencia.id}"]
                NotaCompetencia.objects.create(
                    avaliacao=avaliacao,
                    competencia=competencia,
                    nivel=nivel,
                )

            messages.success(request, "Avaliação criada com sucesso.")
            return redirect("dashboard")
    else:
        form = AvaliacaoForm(initial={"aluno": aluno_id} if aluno_id else None)

    return render(request, "accounts/nova_avaliacao.html", {"form": form})


@login_required
def avaliacoes_aluno(request, aluno_id):
    aluno = get_object_or_404(User, id=aluno_id, groups__name="Alunos")
    avaliacoes = Avaliacao.objects.filter(aluno=aluno).select_related("professor").prefetch_related("notas__competencia")
    return render(request, "accounts/avaliacoes_aluno.html", {"aluno": aluno, "avaliacoes": avaliacoes})


@login_required
@diretor_required
def lista_professores(request):
    busca = request.GET.get("q")

    professores = User.objects.filter(groups__name="Professores")
    if not is_diretor(request.user):
        professores = professores.filter(is_active=True)

    if busca:
        professores = professores.filter(first_name__icontains=busca)

    return render(request, "accounts/lista_professores.html", {"professores": professores, "busca": busca})


@login_required
def lista_alunos(request):
    busca = request.GET.get("q")

    alunos = User.objects.filter(groups__name="Alunos")
    if not is_diretor(request.user):
        alunos = alunos.filter(is_active=True)

    if busca:
        alunos = alunos.filter(first_name__icontains=busca)

    return render(request, "accounts/lista_alunos.html", {"alunos": alunos, "busca": busca})


@login_required
def detalhe_aluno(request, id):
    aluno = get_object_or_404(Aluno, user__id=id)

    if request.method == "POST":
        aluno.user.first_name = request.POST.get("nome")
        aluno.user.last_name = request.POST.get("sobrenome")
        aluno.user.email = request.POST.get("email")

        aluno.cpf = request.POST.get("cpf")
        aluno.telefone = request.POST.get("telefone")
        aluno.endereco = request.POST.get("endereco")

        aluno.user.save()
        aluno.save()
        return redirect("lista_alunos")

    return render(request, "accounts/detalhe_aluno.html", {"aluno": aluno})


@login_required
@diretor_required
def detalhe_professor(request, id):
    professor = get_object_or_404(Professor, user__id=id)

    if request.method == "POST":
        professor.user.first_name = request.POST.get("nome")
        professor.user.last_name = request.POST.get("sobrenome")
        professor.user.email = request.POST.get("email")

        professor.cpf = request.POST.get("cpf")
        professor.telefone = request.POST.get("telefone")
        professor.endereco = request.POST.get("endereco")

        professor.user.save()
        professor.save()
        return redirect("lista_professores")

    return render(request, "accounts/detalhe_professor.html", {"professor": professor})


def criar_aluno(request):
    if request.method == "POST":
        form = AlunoForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data["nome"]
            sobrenome = form.cleaned_data["sobrenome"]
            email = form.cleaned_data["email"]

            senha_temporaria = secrets.token_urlsafe(8)
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=nome,
                last_name=sobrenome,
                password=senha_temporaria,
            )

            aluno = form.save(commit=False)
            aluno.user = user
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
            nome = form.cleaned_data["nome"]
            sobrenome = form.cleaned_data["sobrenome"]
            email = form.cleaned_data["email"]

            senha_temporaria = secrets.token_urlsafe(8)
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=nome,
                last_name=sobrenome,
                password=senha_temporaria,
            )

            professor = form.save(commit=False)
            professor.user = user
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
