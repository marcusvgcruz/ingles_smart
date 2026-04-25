from datetime import date
from .forms import AlunoForm, ProfessorForm, LoginForm
from accounts.models import Perfil, matriculas_ativas
import secrets
from django.db.models import Q, Count, Avg
from django.db.models.functions import TruncDate
from datetime import timedelta, date
from collections import OrderedDict
from django.utils.dateparse import parse_date
from collections import defaultdict
from calendar import monthrange
import calendar
from django.utils import timezone

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

from .forms import AlunoForm, AvaliacaoForm, ProfessorForm, TurmaForm, MatriculaForm, TimeBlockForm, BlockedPeriodForm, CompetenciaForm, NivelForm, ScheduleTemplateForm, PostForm
from .models import (
    Aluno,
    Lesson,
    Avaliacao,
    Competencia,
    Nivel,
    NotaCompetencia,
    Perfil,
    Presenca,
    Professor,
    Turma,
    TurmaHorario,
    Matricula,
    Lesson,
    TimeBlock,
    ScheduleTemplate,
    BlockedPeriod,
    Post,
    PostImagem,
    PostArquivo,
    TarefaAluno,
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
    authentication_form = LoginForm

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

import json
@login_required
def dashboard(request):

    # =========================
    # KPIs
    # =========================
    total_alunos = Aluno.objects.count()

    total_presencas = Presenca.objects.count()
    presencas_presentes = Presenca.objects.filter(presente=True).count()

    presenca_media = int((presencas_presentes / total_presencas) * 100) if total_presencas else 0

    total_avaliacoes = Avaliacao.objects.count()

    media_geral = NotaCompetencia.objects.aggregate(media=Avg("nivel__ordem"))["media"]
    media_geral = round(media_geral, 1) if media_geral else 0

    # =========================
    # GRÁFICO PRESENÇA
    # =========================
    presenca_por_dia = (
        Presenca.objects
        .annotate(dia=TruncDate("created_at"))
        .values("dia")
        .annotate(
            total=Count("id"),
            presentes=Count("id", filter=Q(presente=True))
        )
        .order_by("dia")
    )

    labels = [p["dia"].strftime("%d/%m") for p in presenca_por_dia]
    valores = [
        int((p["presentes"] / p["total"]) * 100) if p["total"] else 0
        for p in presenca_por_dia
    ]

    # =========================
    # GRÁFICO NÍVEIS (pizza)
    # =========================
    tipos = list(
        Aluno.objects.values('tipo').annotate(total=Count('id'))
    )

    # =========================
    # RANKING
    # =========================
    ranking_query = (
        NotaCompetencia.objects
        .values(
            "avaliacao__aluno__id",
            "avaliacao__aluno__first_name",
            "avaliacao__aluno__last_name"
        )
        .annotate(media=Avg("nivel__ordem"))
        .order_by("-media")
    )

    ranking = []

    for index, r in enumerate(ranking_query[:10], start=1):
        ranking.append({
            "posicao": index,
            "nome": f"{r['avaliacao__aluno__first_name']} {r['avaliacao__aluno__last_name']}",
            "media": round(r["media"], 1) if r["media"] else 0
        })

    context = {
        # KPIs
        "total_alunos": total_alunos,
        "presenca_media": presenca_media,
        "media_geral": media_geral,
        "total_avaliacoes": total_avaliacoes,

        # gráficos
        "grafico_presenca_labels": json.dumps(labels),
        "grafico_presenca_valores": json.dumps(valores),

        "tipos": json.dumps(tipos),
        

        # ranking
        "ranking": ranking
    }

    return render(request, "accounts/dashboard.html", context)


def _pode_gerenciar_turma(user):
    return is_professor(user) or is_diretor(user)

@login_required
def turma_calendar(request, turma_id):
    turma = get_object_or_404(Turma, id=turma_id)

    today = now().date()

    # pegar semana atual (segunda a domingo)
    start_week = today - timedelta(days=today.weekday())
    end_week = start_week + timedelta(days=6)

    lessons = turma.lessons.filter(
        date__range=(start_week, end_week)
    ).order_by("date", "start_time")

    # organizar por dia
    calendar = {}
    for i in range(7):
        day = start_week + timedelta(days=i)
        calendar[day] = lessons.filter(date=day)

    return render(request, "accounts/turma_calendar.html", {
        "turma": turma,
        "calendar": calendar,
        "start_week": start_week,
        "end_week": end_week,
    })


@login_required
def lista_turmas(request):

    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden(
            "Apenas professores e diretoria podem gerenciar turmas."
        )

    hoje = timezone.now().date()

    turmas = Turma.objects.prefetch_related(
        "lessons",
        "matricula_set"
    ).all()

    for turma in turmas:
        turma.future_lessons = turma.lessons.filter(
            date__gte=hoje
        ).order_by("date")[:10]

    return render(request, "accounts/lista_turmas.html", {
        "turmas": turmas
    })

def detalhe_turma(request, turma_id):

    turma = get_object_or_404(Turma, id=turma_id)

    hoje = now().date()

    lessons = turma.lessons.filter(date__gte=hoje).order_by("date")[:2]

    matriculas = turma.matricula_set.select_related("aluno", "aluno__user")

    return render(request, "accounts/detalhe_turma.html", {
        "turma": turma,
        "lessons": lessons,
        "matriculas": matriculas
    })


@login_required
def criar_turma(request):

    if request.method == "POST":

        form = TurmaForm(request.POST)

        if form.is_valid():
            form.save()

            return redirect("lista_turmas")

    else:

        form = TurmaForm()

    return render(request, "accounts/criar_turma.html", {
        "form": form
    })


@login_required
def editar_turma(request, turma_id):

    turma = get_object_or_404(Turma, id=turma_id)

    if request.method == "POST":

        form = TurmaForm(request.POST, instance=turma)

        if form.is_valid():
            form.save()
            return redirect("lista_turmas")

    else:
        form = TurmaForm(instance=turma)

    return render(request, "accounts/form_turma.html", {
        "form": form,
        "titulo": "Editar turma"
    })


def gerar_lessons(request, turma_id):

    turma = get_object_or_404(Turma, id=turma_id)

    if not turma.start_date or not turma.end_date:
        messages.error(request, "Turma precisa ter data início e fim.")
        return redirect("detalhe_turma", turma_id=turma.id)

    timeblocks = turma.time_blocks.all()

    if not timeblocks.exists():
        messages.error(request, "Turma não possui horários configurados.")
        return redirect("detalhe_turma", turma_id=turma.id)

    blocked_periods = BlockedPeriod.objects.all()

    current = turma.start_date

    created = 0

    while current <= turma.end_date:

        weekday = current.weekday()

        blocks = timeblocks.filter(weekday=weekday)

        for block in blocks:

            bloqueado = False

            for periodo in blocked_periods:
                if periodo.start_date <= current <= periodo.end_date:
                    bloqueado = True
                    break

            if bloqueado:
                continue

            existe = Lesson.objects.filter(
                class_group=turma,
                date=current,
                start_time=block.start_time
            ).exists()

            if not existe:

                Lesson.objects.create(
                    class_group=turma,
                    room=turma.room,
                    date=current,
                    start_time=block.start_time,
                    end_time=block.end_time
                )

                created += 1

        current += timedelta(days=1)

    messages.success(request, f"{created} aulas geradas com sucesso.")

    return redirect("detalhe_turma", turma_id=turma.id)  


from django.utils.timezone import now

@login_required
def lessons_today(request):
    hoje = now().date()

    lessons = Lesson.objects.filter(date=hoje).order_by("start_time")

    return render(request, "accounts/lessons_today.html", {
        "lessons": lessons
    })

@login_required
def marcar_presenca_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    matriculas = Matricula.objects.filter(turma=lesson.class_group)

    alunos_ativos = [
        m.aluno for m in matriculas
        if m.ativa_na_data(lesson.date)
    ]

    if request.method == "POST":
        for aluno in alunos_ativos:
            presente = request.POST.get(f"aluno_{aluno.id}") == "on"

            Presenca.objects.update_or_create(
                aula=lesson,
                aluno=aluno.user,
                defaults={"presente": presente}
            )

        messages.success(request, "Attendance saved successfully.")
        return redirect("alguma_view")

    return render(request, "accounts/marcar_presenca.html", {
        "lesson": lesson,
        "alunos": alunos_ativos
    })

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Post, PostImagem, PostArquivo
from .forms import PostForm


@login_required
def feed(request):
    posts = Post.objects.all().order_by('-is_fixo', '-criado_em')

    # Se for professor → pode postar
    if request.user.is_staff:
        if request.method == 'POST':
            form = PostForm(request.POST, request.FILES)

            if form.is_valid():
                post = form.save(commit=False)
                post.autor = request.user
                post.save()

                # imagens
                for img in request.FILES.getlist('imagens'):
                    PostImagem.objects.create(post=post, imagem=img)

                # arquivos
                for arq in request.FILES.getlist('arquivos'):
                    PostArquivo.objects.create(post=post, arquivo=arq)

                return redirect('feed')
        else:
            form = PostForm()
    else:
        form = None  # aluno não pode postar

    return render(request, 'accounts/feed.html', {
        'form': form,
        'posts': posts
    })

@login_required
def deletar_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # regra de permissão
    if request.user == post.autor or request.user.is_diretor:
        post.delete()
        return redirect('feed')
    else:
        return HttpResponseForbidden()

    
@login_required
def editar_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.user != post.autor:
        return HttpResponseForbidden()

    if request.method == 'POST':
        conteudo = request.POST.get('conteudo')
        post.conteudo = conteudo
        post.save()
        return redirect('feed')

    return render(request, 'accounts/editar_post.html', {'post': post})

@login_required
def fixar_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # permissão
    if request.user != post.autor and not request.user.is_superuser:
        return HttpResponseForbidden()

    # remover fixo anterior
    Post.objects.filter(is_fixo=True).update(is_fixo=False)

    # fixar atual
    post.is_fixo = True
    post.save()

    return redirect('feed')


@login_required
def desfazer_fixo(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.user != post.autor and not request.user.is_superuser:
        return HttpResponseForbidden()

    post.is_fixo = False
    post.save()

    return redirect('feed')

@login_required
def nova_avaliacao(request):

    aluno_id = request.GET.get("aluno")
    next_url = request.GET.get("next")

    aluno = None

    if aluno_id:
        aluno = User.objects.filter(id=aluno_id).first()

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
                nivel_id = form.cleaned_data[f"competencia_{competencia.id}"]

                if nivel_id:
                    nivel = Nivel.objects.get(id=nivel_id)

                    NotaCompetencia.objects.create(
                        avaliacao=avaliacao,
                        competencia=competencia,
                        nivel=nivel
                    )

            messages.success(request, "Avaliação criada com sucesso.")

            return redirect(f"/avaliacao/aluno/{aluno.id}/?next={next_url}")

    else:
        form = AvaliacaoForm(initial={"aluno": aluno_id} if aluno_id else None)

    return render(request, "accounts/nova_avaliacao.html", {
        "form": form,
        "next": next_url,
        "aluno": aluno
    })


@login_required
def avaliacoes_aluno(request, aluno_id):

    aluno = get_object_or_404(User, id=aluno_id)

    avaliacoes = (
        Avaliacao.objects
        .filter(aluno=aluno)
        .select_related("professor")
        .prefetch_related("notas__competencia")
    )

    next_url = request.GET.get("next")


    return render(
        request,
        "accounts/avaliacoes_aluno.html",
        {
            "aluno": aluno,
            "avaliacoes": avaliacoes,
            "next": next_url
        }
    )

def lista_competencias(request):

    competencias = Competencia.objects.all().order_by("ordem")
    niveis = Nivel.objects.all().order_by("ordem")

    form_nivel = NivelForm()

    return render(
        request,
        "accounts/lista_competencias.html",
        {
            "competencias": competencias,
            "niveis": niveis,
            "form_nivel": form_nivel
        }
    )


def nova_competencia(request):

    if request.method == "POST":

        form = CompetenciaForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Competência criada com sucesso.")
            return redirect("lista_competencias")

    else:
        form = CompetenciaForm()

    return render(
        request,
        "accounts/form_competencia.html",
        {"form": form, "titulo": "Nova Competência"}
    )


def editar_competencia(request, id):

    competencia = get_object_or_404(Competencia, id=id)

    if request.method == "POST":

        form = CompetenciaForm(request.POST, instance=competencia)

        if form.is_valid():
            form.save()
            messages.success(request, "Competência atualizada.")
            return redirect("lista_competencias")

    else:
        form = CompetenciaForm(instance=competencia)

    return render(
        request,
        "accounts/form_competencia.html",
        {"form": form, "titulo": "Editar Competência"}
    )


def criar_nivel(request):

    if request.method == "POST":

        form = NivelForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Nível criado com sucesso.")
            return redirect("lista_competencias")

    else:
        form = NivelForm()

    return render(
        request,
        "accounts/form_nivel.html",
        {"form": form, "titulo": "Novo Nível"}
    )

def editar_nivel(request, id):

    nivel = get_object_or_404(Nivel, id=id)

    if request.method == "POST":

        form = NivelForm(request.POST, instance=nivel)

        if form.is_valid():
            form.save()
            messages.success(request, "Nível atualizado.")
            return redirect("lista_competencias")

    else:
        form = NivelForm(instance=nivel)

    return render(
        request,
        "accounts/form_nivel.html",
        {"form": form, "titulo": "Editar Nível"}
    )


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

    avaliacoes = Avaliacao.objects.filter(aluno=aluno.user)

    ultima_avaliacao = avaliacoes.first()

    # Média geral
    media_avaliacao = (
        NotaCompetencia.objects.filter(avaliacao__aluno=aluno.user).aggregate(media=Avg("nivel__ordem"))
    )["media"]

    # Quantidade de avaliações
    total_avaliacoes = avaliacoes.count()

    # Primeira avaliação (para calcular progresso)
    primeira_avaliacao = avaliacoes.last()

    media_inicial = None
    progresso = None

    if primeira_avaliacao:
        media_inicial = (
            NotaCompetencia.objects.filter(avaliacao=primeira_avaliacao).aggregate(media=Avg("nivel__ordem"))
        )["media"]

    if media_avaliacao is not None and media_inicial is not None:
        progresso = media_avaliacao - media_inicial

    if request.method == "POST":

        if "tarefa_id" in request.POST:
            tarefa = TarefaAluno.objects.get(id=request.POST["tarefa_id"])
            tarefa.concluido = not tarefa.concluido
            tarefa.save()
            return redirect("detalhe_aluno", id=id)

        if "salvar_aluno" in request.POST:
            form = AlunoForm(request.POST, instance=aluno)
            form_matricula = MatriculaForm(initial={"aluno": aluno})

            if form.is_valid():
                form.save()
                return redirect("detalhe_aluno", id=id)

        elif "criar_matricula" in request.POST:

            form = AlunoForm(instance=aluno)
            form_matricula = MatriculaForm(request.POST)

            if form_matricula.is_valid():

                matricula = form_matricula.save(commit=False)
                matricula.aluno = aluno
                matricula.save()

                messages.success(request, "Matrícula criada com sucesso.")

                return redirect("detalhe_aluno", id=id)

            else:
                print(form_matricula.errors)  # debug

    else:
        form = AlunoForm(instance=aluno)
        form_matricula = MatriculaForm(initial={"aluno": aluno})

    

    matriculas = matriculas_ativas(aluno)
    attendance_rate = calcular_presenca_aluno(aluno)

    return render(request, "accounts/detalhe_aluno.html", {
        "aluno": aluno,
        "form": form,
        "media_avaliacao": media_avaliacao,
        "ultima_avaliacao": ultima_avaliacao,
        "total_avaliacoes": total_avaliacoes,
        "progresso": progresso,
        "form_matricula": form_matricula,
        "matriculas": matriculas,
        "today": timezone.now().date(),
        "attendance_rate": attendance_rate
    })

def editar_matricula(request, matricula_id):

    matricula = get_object_or_404(Matricula, id=matricula_id)

    if request.method == "POST":

        form = MatriculaForm(request.POST, instance=matricula)

        if form.is_valid():
            form.save()
            return redirect("detalhe_aluno", id=matricula.aluno.user.id)

    else:
        form = MatriculaForm(instance=matricula)

    return render(request, "accounts/editar_matricula.html", {
        "form": form,
        "matricula": matricula
    })


def finalizar_matricula(request, matricula_id):

    matricula = get_object_or_404(Matricula, id=matricula_id)

    if request.method == "POST":

        matricula.data_fim = timezone.now().date()
        matricula.save()

        messages.success(request, "Matrícula finalizada com sucesso.")

        return redirect("detalhe_aluno", id=matricula.aluno.user.id)
    
        

    return redirect("detalhe_aluno", id=matricula.aluno.user.id)


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


def promover_coordenador(request, user_id):

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":

        grupo_diretoria, created = Group.objects.get_or_create(name="Diretoria")

        user.groups.add(grupo_diretoria)

        messages.success(request, f"{user.first_name} {user.last_name} promovido para Coordenador")

    return redirect("detalhe_professor", id=user_id)

import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from .models import Perfil


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
    aluno.desativado_por = request.user
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

@login_required
def criar_matricula(request):

    aluno_id = request.GET.get("aluno")

    if aluno_id:
        form = MatriculaForm(initial={"aluno": aluno_id})
    else:
        form = MatriculaForm()

    return render(request, "accounts/criar_matricula.html", {"form": form})

def lista_matriculas(request):

    busca = request.GET.get("busca")

    matriculas = Matricula.objects.select_related("aluno", "turma", "aluno__user")

    if busca:
        matriculas = matriculas.filter(
            aluno__user__first_name__icontains=busca
        )

    context = {
        "matriculas": matriculas,
        "busca": busca,
    }

    return render(request, "accounts/lista_matriculas.html", context)


@login_required
def agenda(request):
    start_param = request.GET.get("start")

    if start_param:
        base = parse_date(start_param)
    else:
        base = now().date()

    limite = base + timedelta(days=30)

    lessons = Lesson.objects.filter(
        date__range=(base, limite)
    ).select_related("class_group").order_by("date", "start_time")

    agenda = OrderedDict()

    for lesson in lessons:
        agenda.setdefault(lesson.date, []).append(lesson)

    return render(request, "accounts/agenda.html", {
        "agenda": agenda,
        "base": base,
        "limite": limite,
    })


def agenda_mes(request):

    today = date.today()

    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    blocked_periods = BlockedPeriod.objects.all()

    cal = calendar.Calendar(firstweekday=0)  # Monday

    # matriz de semanas do mês
    month_days = cal.monthdatescalendar(year, month)

    first_day = month_days[0][0]
    last_day = month_days[-1][-1]

    lessons = Lesson.objects.filter(date__range=(first_day, last_day))

    lessons_por_dia = defaultdict(list)

    for lesson in lessons:
        lessons_por_dia[lesson.date].append(lesson)

    calendar_weeks = []

    for week in month_days:
        week_days = []

        for day in week:

            is_blocked = False
            blocked_name = None

            for period in blocked_periods:
                if period.start_date <= day <= period.end_date:
                    is_blocked = True
                    blocked_name = period.name
                    break

            week_days.append({
                "date": day,
                "day": day.day,
                "lessons": lessons_por_dia.get(day, []),
                "is_current_month": day.month == month,
                "blocked": is_blocked,
                "blocked_name": blocked_name
            })

        calendar_weeks.append(week_days)

    # navegação entre meses
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    context = {
        "year": year,
        "month": month,
        "calendar_weeks": calendar_weeks,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
    }

    return render(request, "accounts/agenda_mes.html", context)

def agenda_dia(request, year, month, day):

    data = date(year, month, day)

    lessons = Lesson.objects.filter(
        date=data
    ).select_related(
        "class_group",
        "room"
    ).annotate(
        alunos_ativos=Count(
            "class_group__matricula",
            filter=Q(
                class_group__matricula__data_inicio__lte=data
            ) & (
                Q(class_group__matricula__data_fim__isnull=True) |
                Q(class_group__matricula__data_fim__gte=data)
            ),
            distinct=True
        )
    ).order_by("start_time")

    periods = {
        "morning": {},
        "afternoon": {},
        "night": {}
    }

    for lesson in lessons:

        if lesson.start_time.hour < 12:
            period = "morning"

        elif lesson.start_time.hour < 18:
            period = "afternoon"

        else:
            period = "night"

        room = lesson.room

        if room not in periods[period]:
            periods[period][room] = []

        periods[period][room].append(lesson)

    context = {
        "data": data,
        "periods": periods,
    }

    return render(request, "accounts/agenda_dia.html", context)

def lesson_detail(request, lesson_id):

    lesson = get_object_or_404(Lesson, id=lesson_id)

    # 🔥 DATA DA AULA (ESSENCIAL)
    hoje = lesson.date

    # 🔥 FILTRO CORRETO DE MATRÍCULAS (RESOLVE O BUG)
    matriculas = Matricula.objects.filter(
        turma=lesson.class_group,
        data_inicio__lte=hoje
    ).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gte=hoje)
    ).select_related("aluno")

    # 🔥 GARANTE QUE EXISTE PRESENÇA PARA CADA MATRÍCULA
    presencas = []

    for matricula in matriculas:
        presenca, created = Presenca.objects.get_or_create(
            lesson=lesson,
            matricula=matricula
        )
        presencas.append(presenca)

    # =========================
    # POST (SALVAR PRESENÇA / REPOSIÇÃO)
    # =========================
    if request.method == "POST":

        # 🔁 MARCAR REPOSIÇÃO
        if "reposicao_id" in request.POST:
            presenca_id = request.POST.get("reposicao_id")
            presenca = Presenca.objects.get(id=presenca_id)

            presenca.reposicao = True
            presenca.save()

            return redirect("lesson_detail", lesson_id=lesson.id)

        # ✅ SALVAR PRESENÇAS
        for presenca in presencas:
            checkbox = request.POST.get(f"presenca_{presenca.id}")

            presenca.presente = bool(checkbox)
            presenca.save()

        return redirect("lesson_detail", lesson_id=lesson.id)

    # =========================
    # CONTEXTO
    # =========================
    context = {
        "lesson": lesson,
        "presencas": presencas
    }

    return render(request, "accounts/lesson_detail.html", context)


from .models import ScheduleTemplate

def lista_templates(request):

    templates = ScheduleTemplate.objects.all()

    return render(request, "accounts/templates.html", {
        "templates": templates
    })

def criar_template(request):

    if request.method == "POST":

        form = ScheduleTemplateForm(request.POST)

        if form.is_valid():
            template = form.save()

            return redirect("detalhe_template", id=template.id)

    else:
        form = ScheduleTemplateForm()

    return render(
        request,
        "accounts/criar_template.html",
        {
            "form": form
        }
    )

def detalhe_template(request, id):

    template = get_object_or_404(ScheduleTemplate, id=id)

    blocks = template.blocks.all().order_by("weekday", "start_time")

    form = TimeBlockForm()

    context = {
        "template": template,
        "blocks": blocks,
        "form": form,
    }

    return render(request, "accounts/detalhe_template.html", context)


def add_timeblock(request, id):

    template = get_object_or_404(ScheduleTemplate, id=id)

    if request.method == "POST":

        form = TimeBlockForm(request.POST)

        if form.is_valid():

            block = form.save(commit=False)
            block.template = template
            block.save()

    return redirect("detalhe_template", id=id)

def editar_timeblock(request, id):

    block = get_object_or_404(TimeBlock, id=id)
    template = block.template

    if request.method == "POST":

        form = TimeBlockForm(request.POST, instance=block)

        if form.is_valid():
            form.save()

            return redirect("detalhe_template", id=template.id)

    else:

        form = TimeBlockForm(instance=block)

    return render(request, "accounts/editar_timeblock.html", {
        "form": form,
        "block": block,
        "template": template
    })

def delete_timeblock(request, id):

    block = get_object_or_404(TimeBlock, id=id)

    template_id = block.template.id

    block.delete()

    return redirect("detalhe_template", id=template_id)

def lista_blocked_periods(request):

    periods = BlockedPeriod.objects.all().order_by("-start_date")

    return render(request, "accounts/blocked_periods.html", {
        "periods": periods
    })

def criar_blocked_period(request):

    if request.method == "POST":

        form = BlockedPeriodForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("lista_blocked_periods")

    else:

        form = BlockedPeriodForm()

    return render(request, "accounts/criar_blocked_period.html", {
        "form": form
    })

def delete_blocked_period(request, id):

    period = get_object_or_404(BlockedPeriod, id=id)

    period.delete()

    return redirect("lista_blocked_periods")

def calcular_presenca_aluno(aluno):

    total = Presenca.objects.filter(
        matricula__aluno=aluno
    ).count()

    presentes = Presenca.objects.filter(
        matricula__aluno=aluno,
        presente=True
    ).count()

    if total == 0:
        return 0

    return round((presentes / total) * 100)