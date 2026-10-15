from datetime import date
from .forms import AlunoForm, ProfessorForm, LoginForm
from .html_sanitize import sanitizar_html
from .models import Perfil, matriculas_ativas
import secrets
from django.db.models import Q, Count, Avg, F, Sum, Prefetch, Max
from django.db.models.functions import TruncDate, TruncMonth
from datetime import timedelta, date
from collections import OrderedDict
from django.utils.dateparse import parse_date
from collections import defaultdict
from calendar import monthrange
import calendar
from datetime import time
from datetime import datetime
from django.utils import timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from urllib.parse import urlencode
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy

from .forms import (
    AlunoForm, AvaliacaoForm, ProfessorForm, TurmaForm, MatriculaForm, TimeBlockForm, BlockedPeriodForm,
    CompetenciaForm, NivelForm, ScheduleTemplateForm, PostForm, OnboardingItemForm, PerfilForm,
    GamificationChallengeForm, FinancialEntryForm, ContractForm, EsqueciSenhaForm, EstrategiaForm,
)
from .models import Perfil
from academico.models import (
    Aluno,
    Lesson,
    Nivel,
    Presenca,
    Professor,
    Turma,
    Room,
    TurmaHorario,
    Matricula,
    TimeBlock,
    ScheduleTemplate,
    BlockedPeriod,
    ReposicaoAgendada,
)
from avaliacoes.models import (
    Avaliacao,
    Competencia,
    NotaCompetencia,
)
from feed.models import (
    Post,
    PostImagem,
    PostArquivo,
    TarefaAluno,
)
from onboarding.models import (
    OnboardingItem,
    OnboardingAlunoItem,
)
from gamificacao.models import (
    GamificationChallenge,
    GamificationSubmission,
    GamificationChallengeMedia,
    GamificationSubmissionMedia,
)
from estrategias.models import (
    Estrategia,
    EstrategiaAlunoAcesso,
)
from financeiro.models import (
    FinancialEntry,
    Contract,
)
from .email_utils import enviar_senha_provisoria
from .password_service import redefinir_senha_e_enviar_email
from .permissions import (
    deve_forcar_troca_senha,
    diretor_required,
    is_aluno,
    is_diretor,
    is_professor,
    professor_required,
)


def _redirect_apos_troca_senha(user):
    if is_aluno(user):
        return redirect("feed")
    return redirect("dashboard")


def _mensagem_resultado_email(request, ok, erro, email_destino):
    if ok:
        messages.success(
            request,
            f"Temporary password sent to {email_destino}. "
            "Check your inbox and spam folder (it may take a few minutes).",
        )
    else:
        messages.error(
            request,
            f"The password was updated in the system, but the email was NOT sent: {erro}",
        )


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    authentication_form = LoginForm

    def get_success_url(self):
        user = self.request.user
        if deve_forcar_troca_senha(user):
            return reverse_lazy("trocar_senha")
        if is_professor(user):
            return reverse_lazy("dashboard")
        if is_aluno(user):
            return reverse_lazy("feed")
        return reverse_lazy("dashboard")


@login_required
def trocar_senha(request):
    perfil = getattr(request.user, "perfil", None)
    troca_obrigatoria = deve_forcar_troca_senha(request.user)

    if request.method == "POST":
        current = request.POST.get("current_password", "")
        new_pw = request.POST.get("new_password", "")
        confirm = request.POST.get("confirm_password", "")

        if not troca_obrigatoria and not request.user.check_password(current):
            messages.error(request, "Current password is incorrect.")
        elif len(new_pw) < 8:
            messages.error(request, "The new password must be at least 8 characters.")
        elif new_pw != confirm:
            messages.error(request, "Confirmation does not match the new password.")
        else:
            request.user.set_password(new_pw)
            request.user.save()
            update_session_auth_hash(request, request.user)
            if perfil:
                perfil.deve_trocar_senha = False
                perfil.save(update_fields=["deve_trocar_senha"])
            messages.success(request, "Password updated successfully.")
            return _redirect_apos_troca_senha(request.user)

    template = "accounts/trocar_senha_obrigatoria.html" if troca_obrigatoria else "accounts/trocar_senha.html"
    return render(request, template, {"troca_obrigatoria": troca_obrigatoria})


def esqueci_senha(request):
    if request.user.is_authenticated:
        if deve_forcar_troca_senha(request.user):
            return redirect("trocar_senha")
        return redirect("dashboard")

    if request.method == "POST":
        form = EsqueciSenhaForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip()
            usuario = (
                User.objects.filter(is_active=True)
                .filter(Q(email__iexact=email) | Q(username__iexact=email))
                .first()
            )
            if usuario:
                ok, erro = redefinir_senha_e_enviar_email(usuario, request=request)
                if not ok:
                    messages.error(
                        request,
                        "Could not send the email. Try again later or contact the school office.",
                    )
                    return render(request, "accounts/esqueci_senha.html", {"form": form})
            messages.success(
                request,
                "If the email is registered, you will receive a temporary password shortly. Also check your spam folder.",
            )
            return redirect("login")
    else:
        form = EsqueciSenhaForm()

    return render(request, "accounts/esqueci_senha.html", {"form": form})


@login_required
def resetar_senha(request, user_id):
    if not (is_professor(request.user) or is_diretor(request.user)):
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        destinatario = (user.email or user.username or "").strip()
        ok, erro = redefinir_senha_e_enviar_email(user, request=request)
        _mensagem_resultado_email(request, ok, erro, destinatario)
        return redirect("detalhe_aluno", id=user.id)

    return redirect("lista_alunos")


@login_required
def resetar_senha_professor(request, user_id):
    if not is_diretor(request.user):
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        destinatario = (user.email or user.username or "").strip()
        ok, erro = redefinir_senha_e_enviar_email(user, request=request)
        _mensagem_resultado_email(request, ok, erro, destinatario)
        return redirect("detalhe_professor", id=user.id)

    return redirect("lista_professores")


User = get_user_model()

import json


def _can_publish_feed(user):
    return is_professor(user) or is_diretor(user)

def _is_management_user(user):
    return is_professor(user) or is_diretor(user)


def _contracts_income_for_calendar_month(year, month):
    """Sum monthly fees for contracts active during that calendar month."""
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    agg = (
        Contract.objects.filter(ativo=True, inicio__lte=end)
        .filter(Q(fim__isnull=True) | Q(fim__gte=start))
        .aggregate(s=Sum("valor_mensal"))
    )
    return float(agg["s"] or 0)


def _contracts_overlapping_period(period_start, period_end):
    return (
        Contract.objects.filter(ativo=True, inicio__lte=period_end)
        .filter(Q(fim__isnull=True) | Q(fim__gte=period_start))
        .select_related("aluno", "aluno__user")
    )


def _apply_contract_income_to_month_map(month_map):
    for key in list(month_map.keys()):
        try:
            mm_s, yy_s = key.split("/")
            mth, yr = int(mm_s), int(yy_s)
        except (ValueError, AttributeError):
            continue
        month_map[key]["income"] += _contracts_income_for_calendar_month(yr, mth)


def _sort_finance_month_keys(keys):
    def key_fn(k):
        mm, yy = k.split("/")
        return (int(yy), int(mm))

    return sorted(keys, key=key_fn)


def _finance_chart_series_last_n(month_map, n=12):
    keys = _sort_finance_month_keys(month_map.keys())[-n:]
    labels, inc, exp = [], [], []
    for key in keys:
        v = month_map[key]
        labels.append(key)
        inc.append(v["income"])
        exp.append(v["expense"])
    return labels, inc, exp


def _finance_chart_for_custom_range(month_map, period_start, period_end):
    labels, inc, exp = [], [], []
    for key in _sort_finance_month_keys(month_map.keys()):
        mm, yy = key.split("/")
        y, m = int(yy), int(mm)
        mstart = date(y, m, 1)
        mend = date(y, m, monthrange(y, m)[1])
        if mend < period_start or mstart > period_end:
            continue
        v = month_map[key]
        labels.append(key)
        inc.append(v["income"])
        exp.append(v["expense"])
    return labels, inc, exp


def _user_avatar_url(user):
    try:
        perfil = user.perfil
        if perfil.avatar:
            return perfil.avatar.url
    except Perfil.DoesNotExist:
        pass
    return None


_FEED_IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "gif", "webp", "bmp"})
_FEED_IMAGE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
)


def _feed_html_is_empty(html):
    import re

    if not html or not str(html).strip():
        return True
    text = re.sub(r"<[^>]+>", "", str(html)).replace("&nbsp;", " ").strip()
    return not text


def _feed_upload_is_valid(uploaded):
    """Ignora inputs file vazios (comum em mobile/PWA no multipart)."""
    if not uploaded:
        return False
    size = getattr(uploaded, "size", None)
    if size is not None:
        return size > 0
    try:
        pos = uploaded.tell()
        uploaded.seek(0, 2)
        size = uploaded.tell()
        uploaded.seek(pos)
        return size > 0
    except Exception:
        return bool(getattr(uploaded, "name", None))


def _feed_has_attachments(files):
    if not files:
        return False
    for key in ("imagens", "arquivos"):
        for uploaded in files.getlist(key):
            if _feed_upload_is_valid(uploaded):
                return True
    return False


def _feed_upload_as_image(uploaded):
    ct = (getattr(uploaded, "content_type", None) or "").lower()
    name = (getattr(uploaded, "name", None) or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ct.startswith("video/"):
        return False
    if ext in _FEED_IMAGE_EXTENSIONS:
        return True
    return ct in _FEED_IMAGE_CONTENT_TYPES


def _persist_feed_attachments(post, files):
    """Imagens compatíveis → PostImagem; vídeos/PDF/HEIC → PostArquivo."""
    errors = []

    def _save(uploaded, force_file=False):
        if not _feed_upload_is_valid(uploaded):
            return
        as_image = not force_file and _feed_upload_as_image(uploaded)
        try:
            if as_image:
                PostImagem.objects.create(post=post, imagem=uploaded)
            else:
                PostArquivo.objects.create(post=post, arquivo=uploaded)
        except Exception as exc:
            label = getattr(uploaded, "name", None) or "file"
            errors.append(f"{label}: {exc}")

    for uploaded in files.getlist("imagens"):
        _save(uploaded)
    for uploaded in files.getlist("arquivos"):
        _save(uploaded, force_file=True)

    return errors


def _student_dashboard_chart_context(aluno):
    """Shared chart series for the student dashboard and director print report."""
    attendance_rate = calcular_presenca_aluno(aluno)
    media_avaliacao = (
        NotaCompetencia.objects.filter(avaliacao__aluno=aluno.user).aggregate(media=Avg("nivel__ordem"))
    )["media"]

    avaliacoes = Avaliacao.objects.filter(aluno=aluno.user).order_by("data")[:20]
    avaliacoes_all = Avaliacao.objects.filter(aluno=aluno.user)
    primeira = avaliacoes_all.last()
    media_inicial = None
    if primeira:
        media_inicial = (
            NotaCompetencia.objects.filter(avaliacao=primeira).aggregate(media=Avg("nivel__ordem"))
        )["media"]
    progresso = None
    if media_avaliacao is not None and media_inicial is not None:
        progresso = float(media_avaliacao) - float(media_inicial)

    performance_labels = ["Attendance", "Evaluation Average", "Progress"]
    performance_values = [
        attendance_rate,
        float(media_avaliacao or 0) * 10,
        float(progresso or 0) * 10,
    ]

    presencas = Presenca.objects.filter(matricula__aluno=aluno).select_related("lesson").order_by("lesson__date")[:20]
    attendance_labels = [p.lesson.date.strftime("%d/%m") for p in presencas]
    attendance_values = [100 if p.presente else 0 for p in presencas]
    evaluation_labels = [a.data.strftime("%d/%m") for a in avaliacoes]
    evaluation_values = []
    for a in avaliacoes:
        avg = NotaCompetencia.objects.filter(avaliacao=a).aggregate(media=Avg("nivel__ordem"))["media"] or 0
        evaluation_values.append(round(float(avg), 1))

    return {
        "attendance_rate": attendance_rate,
        "media_avaliacao": round(float(media_avaliacao or 0), 1),
        "progresso": progresso,
        "presencas": presencas,
        "avaliacoes": avaliacoes,
        "attendance_labels": json.dumps(attendance_labels),
        "attendance_values": json.dumps(attendance_values),
        "evaluation_labels": json.dumps(evaluation_labels),
        "evaluation_values": json.dumps(evaluation_values),
        "performance_labels": json.dumps(performance_labels),
        "performance_values": json.dumps(performance_values),
    }


def _union_contract_month_keys_into_map(month_map):
    """Add month keys for active contracts so contract-only months still show income."""
    today = timezone.now().date()
    for c in Contract.objects.filter(ativo=True):
        cur = date(c.inicio.year, c.inicio.month, 1)
        end_c = c.fim or today
        end_c = date(end_c.year, end_c.month, monthrange(end_c.year, end_c.month)[1])
        while cur <= end_c:
            key = cur.strftime("%m/%Y")
            if key not in month_map:
                month_map[key] = {"income": 0, "expense": 0}
            if cur.month == 12:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 1, 1)


def _student_performance_snapshot():
    alunos = Aluno.objects.select_related("user")
    snapshot = []
    for aluno in alunos:
        attendance = calcular_presenca_aluno(aluno)
        avg = NotaCompetencia.objects.filter(
            avaliacao__aluno=aluno.user
        ).aggregate(media=Avg("nivel__ordem"))["media"] or 0
        score = (attendance * 0.6) + (float(avg) * 10 * 0.4)
        snapshot.append({
            "id": aluno.user.id,
            "nome": aluno.user.get_full_name() or aluno.user.username,
            "attendance": attendance,
            "avg": round(avg, 1),
            "score": round(score, 1),
        })
    return snapshot


def _estrategias_alunos_contagem_dashboard():
    """
    For each student with at least one strategy access, count them only under
    the highest strategy number they have access to (not earlier ones).
    """
    ultima_por_aluno = (
        EstrategiaAlunoAcesso.objects.values("aluno_id")
        .annotate(ultima=Max("estrategia__numero"))
    )
    contagem = {n: 0 for n in range(1, 11)}
    for row in ultima_por_aluno:
        numero = row["ultima"]
        if numero is not None and 1 <= numero <= 10:
            contagem[numero] += 1
    labels = [f"Strategy {n}" for n in range(1, 11)]
    valores = [contagem[n] for n in range(1, 11)]
    return labels, valores


@login_required
def dashboard(request):
    if is_aluno(request.user):
        return redirect("student_dashboard")

    # =========================
    # KPIs
    # =========================
    total_alunos = Aluno.objects.count()

    total_presencas = Presenca.objects.count()
    presencas_presentes = Presenca.objects.filter(presente=True).count()

    presenca_media = int((presencas_presentes / total_presencas) * 100) if total_presencas else 0

    today = timezone.now().date()
    month_start = today.replace(day=1)
    month_end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    lessons_this_month = Lesson.objects.filter(date__gte=month_start, date__lte=month_end).count()
    lessons_today = Lesson.objects.filter(date=today).count()

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

    perf = _student_performance_snapshot()
    top_5_best = sorted(perf, key=lambda x: x["score"], reverse=True)[:5]
    top_5_attention = sorted(perf, key=lambda x: x["score"])[:5]

    estrategias_labels, estrategias_valores = _estrategias_alunos_contagem_dashboard()

    context = {
        # KPIs
        "total_alunos": total_alunos,
        "presenca_media": presenca_media,
        "lessons_this_month": lessons_this_month,
        "lessons_today": lessons_today,

        # gráficos
        "grafico_presenca_labels": json.dumps(labels),
        "grafico_presenca_valores": json.dumps(valores),

        "tipos": json.dumps(tipos),
        "grafico_estrategias_labels": json.dumps(estrategias_labels),
        "grafico_estrategias_valores": json.dumps(estrategias_valores),
        "top_5_best": top_5_best,
        "top_5_attention": top_5_attention,
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
        "today": today,
    })


@login_required
def lista_turmas(request):

    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden(
            "Only Global Makers and board members can manage classes."
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

@login_required
def detalhe_turma(request, turma_id):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()

    turma = get_object_or_404(Turma, id=turma_id)

    hoje = now().date()

    lessons = turma.lessons.filter(date__gte=hoje).order_by("date")[:2]

    matriculas = turma.matricula_set.select_related("aluno", "aluno__user").filter(
        data_inicio__lte=hoje
    ).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gte=hoje)
    )

    return render(request, "accounts/detalhe_turma.html", {
        "turma": turma,
        "lessons": lessons,
        "matriculas": matriculas
    })


def _safe_next_redirect_path(request):
    path = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if path.startswith("/") and not path.startswith("//") and "://" not in path:
        return path
    return None


def _delete_lesson_if_unused(lesson):
    if not lesson:
        return
    if Presenca.objects.filter(lesson=lesson).exists():
        return
    if ReposicaoAgendada.objects.filter(lesson=lesson).exists():
        return
    lesson.delete()


def _resolve_makeup_lesson(turma, data_agendada, horario_inicio, horario_fim, current_lesson=None):
    """
    Return (lesson, error_message_or_none).
    Enforces DB unique (date, start_time, room): reuse same-class slot or update current row in place.
    """
    room = turma.room
    others = Lesson.objects.filter(date=data_agendada, start_time=horario_inicio, room=room)
    if current_lesson:
        others = others.exclude(pk=current_lesson.pk)
    conflict = others.first()
    if conflict:
        if conflict.class_group_id != turma.id:
            return None, (
                "That room is already booked at this date and time for another class. "
                "Choose another time or assign the class to a different room."
            )
        if conflict.end_time != horario_fim:
            conflict.end_time = horario_fim
            conflict.save(update_fields=["end_time"])
        return conflict, None
    if current_lesson:
        current_lesson.class_group = turma
        current_lesson.room = room
        current_lesson.date = data_agendada
        current_lesson.start_time = horario_inicio
        current_lesson.end_time = horario_fim
        try:
            current_lesson.save()
        except IntegrityError:
            return None, "That time slot conflicts with another lesson. Refresh the page and try again."
        return current_lesson, None
    try:
        return (
            Lesson.objects.create(
                class_group=turma,
                room=room,
                date=data_agendada,
                start_time=horario_inicio,
                end_time=horario_fim,
            ),
            None,
        )
    except IntegrityError:
        return None, "That time slot is already in use. Refresh the page and try again."


@login_required
def criar_turma(request):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()

    if request.method == "POST":

        form = TurmaForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Class created.")
            nxt = _safe_next_redirect_path(request)
            if nxt:
                return redirect(nxt)
            return redirect("lista_turmas")

    else:

        form = TurmaForm()

    return render(request, "accounts/criar_turma.html", {
        "form": form,
        "next_path": _safe_next_redirect_path(request),
    })


@login_required
def editar_turma(request, turma_id):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()

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
        "titulo": "Edit class"
    })


@login_required
@diretor_required
def excluir_turma(request, turma_id):
    if request.method != "POST":
        return HttpResponseForbidden()
    turma = get_object_or_404(Turma, id=turma_id)
    name = turma.name
    turma.delete()
    messages.success(request, f'Class "{name}" was deleted.')
    return redirect("lista_turmas")


def gerar_lessons(request, turma_id):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()

    turma = get_object_or_404(Turma, id=turma_id)

    today = timezone.now().date()
    start_date_str = request.GET.get("start_date") or request.POST.get("start_date")
    end_date_str = request.GET.get("end_date") or request.POST.get("end_date")

    start = parse_date(start_date_str) if start_date_str else today
    end = parse_date(end_date_str) if end_date_str else date(today.year, 12, 31)

    timeblocks = turma.time_blocks.all()

    if not timeblocks.exists():
        messages.error(request, "Class has no configured schedule blocks.")
        return redirect("detalhe_turma", turma_id=turma.id)

    blocked_periods = BlockedPeriod.objects.all()

    current = start
    created = 0

    while current <= end:

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

    messages.success(request, f"{created} lessons generated successfully.")

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

@login_required
def feed(request):
    posts_qs = (
        Post.objects.select_related("autor", "autor__perfil")
        .prefetch_related("imagens", "arquivos")
        .order_by("-is_fixo", "-criado_em")
    )
    posts = []
    for post in posts_qs:
        avatar_url = None
        try:
            perfil = post.autor.perfil
            if perfil.avatar:
                avatar_url = perfil.avatar.url
        except Perfil.DoesNotExist:
            pass
        post.feed_avatar_url = avatar_url
        posts.append(post)

    if _can_publish_feed(request.user):
        if request.method == 'POST':
            post_data = request.POST.copy()
            # Garante que o HTML do Quill chegue ao form (hidden #conteudo)
            if request.POST.get("conteudo") is not None:
                post_data["conteudo"] = request.POST.get("conteudo")
            form = PostForm(post_data)

            if form.is_valid():
                has_files = _feed_has_attachments(request.FILES)
                conteudo = form.cleaned_data.get("conteudo") or request.POST.get("conteudo") or ""
                if _feed_html_is_empty(conteudo) and not has_files:
                    messages.error(
                        request,
                        "Write something or attach a file before publishing.",
                    )
                else:
                    try:
                        with transaction.atomic():
                            post = form.save(commit=False)
                            post.autor = request.user
                            post.conteudo = sanitizar_html(conteudo)
                            post.save()
                            upload_errors = (
                                _persist_feed_attachments(post, request.FILES)
                                if has_files
                                else []
                            )
                        if upload_errors:
                            messages.warning(
                                request,
                                "Post published, but some attachments failed: "
                                + "; ".join(upload_errors),
                            )
                        else:
                            messages.success(request, "Post published.")
                        return redirect("feed")
                    except Exception as exc:
                        messages.error(
                            request,
                            f"Could not publish the post: {exc}",
                        )
            else:
                messages.error(
                    request,
                    "Could not publish the post. Check the fields and try again.",
                )
        else:
            form = PostForm()
    else:
        form = None  # aluno não pode postar

    return render(request, 'accounts/feed.html', {
        'form': form,
        'posts': posts
    })

@login_required
@require_POST
def deletar_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.user == post.autor or is_diretor(request.user):
        post.delete()
        return redirect('feed')
    else:
        return HttpResponseForbidden()

    
@login_required
def editar_post(request, post_id):
    post = get_object_or_404(Post.objects.prefetch_related("imagens"), id=post_id)

    if request.user != post.autor:
        return HttpResponseForbidden()

    if request.method == "POST":
        post.conteudo = sanitizar_html(request.POST.get("conteudo") or "")
        post.save()

        remove_ids = request.POST.getlist("remove_image")
        if remove_ids:
            PostImagem.objects.filter(post=post, id__in=remove_ids).delete()

        for img in request.FILES.getlist("imagens"):
            PostImagem.objects.create(post=post, imagem=img)

        messages.success(request, "Post updated.")
        return redirect("feed")

    return render(request, "accounts/editar_post.html", {"post": post})

@login_required
@require_POST
def fixar_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # permissão
    if request.user != post.autor and not is_diretor(request.user):
        return HttpResponseForbidden()

    # remover fixo anterior
    Post.objects.filter(is_fixo=True).update(is_fixo=False)

    # fixar atual
    post.is_fixo = True
    post.save()

    return redirect('feed')


@login_required
@require_POST
def desfazer_fixo(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.user != post.autor and not is_diretor(request.user):
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

            messages.success(request, "Evaluation created successfully.")

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

@login_required
@diretor_required
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


@login_required
@diretor_required
def nova_competencia(request):

    if request.method == "POST":

        form = CompetenciaForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Criterion created successfully.")
            return redirect("lista_competencias")

    else:
        form = CompetenciaForm()

    return render(
        request,
        "accounts/form_competencia.html",
        {"form": form, "titulo": "New evaluation criterion"}
    )


@login_required
@diretor_required
def editar_competencia(request, id):

    competencia = get_object_or_404(Competencia, id=id)

    if request.method == "POST":

        form = CompetenciaForm(request.POST, instance=competencia)

        if form.is_valid():
            form.save()
            messages.success(request, "Criterion updated.")
            return redirect("lista_competencias")

    else:
        form = CompetenciaForm(instance=competencia)

    return render(
        request,
        "accounts/form_competencia.html",
        {"form": form, "titulo": "Edit evaluation criterion"}
    )


@login_required
@diretor_required
def criar_nivel(request):

    if request.method == "POST":

        form = NivelForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Level created successfully.")
            return redirect("lista_competencias")

    else:
        form = NivelForm()

    return render(
        request,
        "accounts/form_nivel.html",
        {"form": form, "titulo": "New proficiency level"}
    )

@login_required
@diretor_required
def editar_nivel(request, id):

    nivel = get_object_or_404(Nivel, id=id)

    if request.method == "POST":

        form = NivelForm(request.POST, instance=nivel)

        if form.is_valid():
            form.save()
            messages.success(request, "Level updated.")
            return redirect("lista_competencias")

    else:
        form = NivelForm(instance=nivel)

    return render(
        request,
        "accounts/form_nivel.html",
        {"form": form, "titulo": "Edit proficiency level"}
    )


@login_required
@diretor_required
def excluir_competencia(request, id):
    if request.method != "POST":
        return HttpResponseForbidden()
    c = get_object_or_404(Competencia, id=id)
    if NotaCompetencia.objects.filter(competencia=c).exists():
        messages.error(
            request,
            "Cannot delete a criterion that already has evaluation scores. Deactivate it instead.",
        )
        return redirect("lista_competencias")
    nome = c.nome
    c.delete()
    messages.success(request, f'Criterion "{nome}" deleted.')
    return redirect("lista_competencias")


@login_required
@diretor_required
def excluir_nivel(request, id):
    if request.method != "POST":
        return HttpResponseForbidden()
    nivel = get_object_or_404(Nivel, id=id)
    if NotaCompetencia.objects.filter(nivel=nivel).exists():
        messages.error(
            request,
            "Cannot delete a proficiency level that is already used in evaluations. Deactivate it instead.",
        )
        return redirect("lista_competencias")
    nome = nivel.nome
    nivel.delete()
    messages.success(request, f'Level "{nome}" deleted.')
    return redirect("lista_competencias")


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
    if not _is_management_user(request.user):
        return HttpResponseForbidden()
    busca = request.GET.get("q")

    alunos = User.objects.filter(groups__name="Alunos")
    if not is_diretor(request.user):
        alunos = alunos.filter(is_active=True)

    if busca:
        alunos = alunos.filter(first_name__icontains=busca)

    alunos = alunos.order_by("first_name", "last_name")
    paginator = Paginator(alunos, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "accounts/lista_alunos.html", {
        "alunos": page_obj,
        "page_obj": page_obj,
        "busca": busca,
    })


@login_required
def detalhe_aluno(request, id):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()

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

        if "onboarding_status_id" in request.POST:
            status = get_object_or_404(OnboardingAlunoItem, id=request.POST["onboarding_status_id"], aluno=aluno)
            status.concluido = not status.concluido
            status.atualizado_por = request.user
            status.save()
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

                messages.success(request, "Enrollment created successfully.")

                return redirect("detalhe_aluno", id=id)

            else:
                print(form_matricula.errors)  # debug

    else:
        form = AlunoForm(instance=aluno)
        form_matricula = MatriculaForm(initial={"aluno": aluno})

    

    for item in OnboardingItem.objects.filter(ativo=True):
        OnboardingAlunoItem.objects.get_or_create(aluno=aluno, item=item)

    matriculas = matriculas_ativas(aluno)
    attendance_rate = calcular_presenca_aluno(aluno)
    onboarding_status = OnboardingAlunoItem.objects.filter(aluno=aluno).select_related("item")

    performance_labels = ["Attendance", "Evaluation Average", "Progress"]
    performance_values = [attendance_rate, float(media_avaliacao or 0) * 10, float(progresso or 0) * 10]

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
        "attendance_rate": attendance_rate,
        "onboarding_status": onboarding_status,
        "performance_labels": json.dumps(performance_labels),
        "performance_values": json.dumps(performance_values),
    })


@login_required
def relatorio_aluno_impressao(request, id):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()
    aluno = get_object_or_404(Aluno, user__id=id)
    ctx = _student_dashboard_chart_context(aluno)
    ctx["aluno"] = aluno
    ctx["generated_at"] = timezone.now()
    ctx["school_name"] = settings.SCHOOL_DISPLAY_NAME
    ctx["auto_print"] = request.GET.get("noprint") != "1"
    return render(request, "accounts/relatorio_aluno_impressao.html", ctx)


def editar_matricula(request, matricula_id):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()

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
    if not _is_management_user(request.user):
        return HttpResponseForbidden()

    matricula = get_object_or_404(Matricula, id=matricula_id)

    if request.method == "POST":

        matricula.data_fim = timezone.now().date() - timedelta(days=1)
        matricula.save()

        messages.success(request, "Enrollment finished successfully.")

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

        messages.success(request, f"{user.first_name} {user.last_name} promoted to Coordinator")

    return redirect("detalhe_professor", id=user_id)

@login_required
def criar_aluno(request):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()

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
            user.perfil.save(update_fields=["deve_trocar_senha"])

            grupo = Group.objects.get(name="Alunos")
            user.groups.add(grupo)

            login_url = request.build_absolute_uri(reverse("login"))
            nome_completo = f"{nome} {sobrenome}".strip()
            ok, erro = enviar_senha_provisoria(
                email,
                senha_temporaria,
                nome=nome_completo,
                login_url=login_url,
            )
            if ok:
                messages.success(
                    request,
                    f"Global Cityzen registered. Temporary password sent to {email} (check spam).",
                )
            else:
                messages.warning(
                    request,
                    f"Global Cityzen registered, but the email was not sent: {erro}",
                )
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


@login_required
@diretor_required
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
            user.perfil.save(update_fields=["deve_trocar_senha"])

            grupo = Group.objects.get(name="Professores")
            user.groups.add(grupo)

            login_url = request.build_absolute_uri(reverse("login"))
            nome_completo = f"{nome} {sobrenome}".strip()
            ok, erro = enviar_senha_provisoria(
                email,
                senha_temporaria,
                nome=nome_completo,
                login_url=login_url,
            )
            if ok:
                messages.success(
                    request,
                    f"Global Maker registered. Temporary password sent to {email} (check spam).",
                )
            else:
                messages.warning(
                    request,
                    f"Global Maker registered, but the email was not sent: {erro}",
                )
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

    # 🔥 AQUI ESTÁ A CORREÇÃO PRINCIPAL
    lessons = Lesson.objects.filter(
        date__range=(first_day, last_day)
    ).annotate(
        alunos_ativos=Count(
            "class_group__matricula",
            filter=Q(
                class_group__matricula__data_inicio__lte=F("date")
            ) & (
                Q(class_group__matricula__data_fim__isnull=True) |
                Q(class_group__matricula__data_fim__gte=F("date"))
            ),
            distinct=True
        )
    ).filter(
        alunos_ativos__gt=0
    )

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

        if "reposicao_add_id" in request.POST:
            presenca_id = request.POST.get("reposicao_add_id")
            presenca = get_object_or_404(Presenca, id=presenca_id, lesson=lesson)
            presenca.reposicao_pendente = 1
            presenca.reposicao = True
            presenca.reposicao_registrada_por = request.user
            presenca.save()
            return redirect("lesson_detail", lesson_id=lesson.id)

        if "reposicao_id" in request.POST:
            presenca_id = request.POST.get("reposicao_id")
            presenca = Presenca.objects.get(id=presenca_id, lesson=lesson)
            presenca.reposicao_pendente += 1
            presenca.reposicao = True
            presenca.reposicao_registrada_por = request.user
            presenca.save()

            return redirect("lesson_detail", lesson_id=lesson.id)

        # ✅ SALVAR PRESENÇAS
        for presenca in presencas:
            checkbox = request.POST.get(f"presenca_{presenca.id}")

            presenca.presente = bool(checkbox)
            if not presenca.presente:
                presenca.reposicao_registrada_por = request.user
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


from academico.models import ScheduleTemplate

@login_required
@diretor_required
def lista_templates(request):

    templates = ScheduleTemplate.objects.all()

    return render(request, "accounts/templates.html", {
        "templates": templates
    })


@login_required
@diretor_required
def delete_template(request, id):
    if request.method != "POST":
        return HttpResponseForbidden()
    template = get_object_or_404(ScheduleTemplate, id=id)
    template.delete()
    messages.success(request, "Template deleted.")
    return redirect("lista_templates")


@login_required
@diretor_required
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

@login_required
@diretor_required
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


def _default_school_slots():
    """40-minute teaching blocks; same start times as before, end 10 minutes earlier."""
    return [
        (time(7, 0), time(7, 40)),
        (time(7, 50), time(8, 30)),
        (time(8, 40), time(9, 20)),
        (time(9, 30), time(10, 10)),
        (time(10, 20), time(11, 0)),
        (time(11, 10), time(11, 50)),
        (time(16, 10), time(16, 50)),
        (time(17, 0), time(17, 40)),
        (time(17, 50), time(18, 30)),
        (time(18, 40), time(19, 20)),
        (time(19, 30), time(20, 10)),
        (time(20, 20), time(21, 0)),
    ]


@login_required
@diretor_required
def aplicar_grade_padrao_template(request, id):
    template = get_object_or_404(ScheduleTemplate, id=id)
    slots = _default_school_slots()
    created = 0
    for weekday in [0, 1, 2, 3, 4]:
        for start_time, end_time in slots:
            _, was_created = TimeBlock.objects.get_or_create(
                template=template,
                weekday=weekday,
                start_time=start_time,
                defaults={"end_time": end_time},
            )
            if was_created:
                created += 1
    for i in range(1, 4):
        Room.objects.get_or_create(name=f"Room {i}")
    messages.success(request, f"Default school schedule applied ({created} blocks created).")
    return redirect("detalhe_template", id=id)


@login_required
@diretor_required
def add_timeblock(request, id):

    template = get_object_or_404(ScheduleTemplate, id=id)

    if request.method == "POST":

        form = TimeBlockForm(request.POST)

        if form.is_valid():

            block = form.save(commit=False)
            block.template = template
            block.save()
            messages.success(request, "Time block saved.")
        else:
            messages.error(request, "Could not save block. Check duplicate day/time and 40-minute duration.")

    return redirect("detalhe_template", id=id)

@login_required
@diretor_required
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

@login_required
@diretor_required
def delete_timeblock(request, id):

    block = get_object_or_404(TimeBlock, id=id)

    template_id = block.template.id

    block.delete()

    return redirect("detalhe_template", id=template_id)

@login_required
@diretor_required
def lista_blocked_periods(request):

    periods = BlockedPeriod.objects.all().order_by("-start_date")

    return render(request, "accounts/blocked_periods.html", {
        "periods": periods
    })

@login_required
@diretor_required
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


@login_required
@diretor_required
def editar_blocked_period(request, id):
    period = get_object_or_404(BlockedPeriod, id=id)
    if request.method == "POST":
        form = BlockedPeriodForm(request.POST, instance=period)
        if form.is_valid():
            form.save()
            messages.success(request, "Blocked period updated.")
            return redirect("lista_blocked_periods")
    else:
        form = BlockedPeriodForm(instance=period)
    return render(request, "accounts/editar_blocked_period.html", {"form": form, "period": period})


@login_required
@diretor_required
def delete_blocked_period(request, id):

    period = get_object_or_404(BlockedPeriod, id=id)

    period.delete()

    return redirect("lista_blocked_periods")


@login_required
@diretor_required
def clear_all_blocked_periods(request):
    if request.method != "POST":
        return HttpResponseForbidden()
    n, _ = BlockedPeriod.objects.all().delete()
    messages.success(
        request,
        f"Cleared {n} recess period(s). Scheduled lessons and history were not changed.",
    )
    return redirect("lista_blocked_periods")


@login_required
@diretor_required
def onboarding_items(request):
    if request.method == "POST":
        if "deactivate_id" in request.POST:
            item = get_object_or_404(OnboardingItem, id=request.POST["deactivate_id"])
            item.ativo = False
            item.save(update_fields=["ativo"])
            messages.success(request, "Onboarding item deactivated.")
            return redirect("onboarding_items")
        if "activate_id" in request.POST:
            item = get_object_or_404(OnboardingItem, id=request.POST["activate_id"])
            item.ativo = True
            item.save(update_fields=["ativo"])
            messages.success(request, "Onboarding item activated.")
            return redirect("onboarding_items")
        if "delete_id" in request.POST:
            item = get_object_or_404(OnboardingItem, id=request.POST["delete_id"])
            item.delete()
            messages.success(request, "Onboarding item deleted.")
            return redirect("onboarding_items")

        form = OnboardingItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Onboarding item created.")
            return redirect("onboarding_items")
    else:
        form = OnboardingItemForm()

    items = OnboardingItem.objects.all()
    return render(request, "accounts/onboarding_items.html", {"form": form, "items": items})


@login_required
def lista_reposicoes(request):
    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden("Only Global Makers and board members can view pending repositions.")

    pendencias = Presenca.objects.filter(
        reposicao_pendente__gt=0
    ).select_related(
        "lesson",
        "lesson__class_group",
        "matricula",
        "matricula__aluno",
        "matricula__aluno__user",
        "reposicao_registrada_por",
    ).order_by("lesson__date", "lesson__start_time")

    historico = (
        ReposicaoAgendada.objects.select_related(
            "presenca",
            "presenca__matricula",
            "presenca__matricula__aluno",
            "presenca__matricula__aluno__user",
            "turma",
            "lesson",
        )
        .order_by("-data_agendada", "-id")[:80]
    )
    return render(request, "accounts/lista_reposicoes.html", {"pendencias": pendencias, "historico": historico})


@login_required
def agendar_reposicao(request, presenca_id):
    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden("Only Global Makers and board members can schedule repositions.")
    presenca = get_object_or_404(
        Presenca.objects.select_related(
            "lesson",
            "lesson__class_group",
            "matricula",
            "matricula__aluno",
            "matricula__aluno__user",
        ),
        id=presenca_id,
    )
    if presenca.reposicao_pendente == 0:
        messages.info(request, "This item no longer has a pending reposition.")
        return redirect("lista_reposicoes")
    turmas = Turma.objects.all().order_by("name")

    if request.method == "POST":
        data_agendada = parse_date(request.POST.get("data_agendada"))
        horario_inicio_raw = request.POST.get("horario_inicio")
        horario_fim_raw = request.POST.get("horario_fim")
        turma_id = request.POST.get("turma_id")
        observacao = request.POST.get("observacao")
        turma = Turma.objects.filter(id=turma_id).first() or presenca.lesson.class_group
        if data_agendada and horario_inicio_raw and horario_fim_raw and turma:
            horario_inicio = datetime.strptime(horario_inicio_raw, "%H:%M").time()
            horario_fim = datetime.strptime(horario_fim_raw, "%H:%M").time()
            reposicao_lesson, err = _resolve_makeup_lesson(
                turma, data_agendada, horario_inicio, horario_fim, current_lesson=None
            )
            if err:
                messages.error(request, err)
            else:
                ReposicaoAgendada.objects.create(
                    presenca=presenca,
                    data_agendada=data_agendada,
                    horario_inicio=horario_inicio,
                    horario_fim=horario_fim,
                    turma=turma,
                    lesson=reposicao_lesson,
                    observacao=observacao,
                    agendada_por=request.user,
                )
                presenca.reposicao_pendente = 0
                presenca.reposicao = False
                presenca.save()
                messages.success(request, "Reposition scheduled and added to the agenda.")
                return redirect("lista_reposicoes")
        else:
            messages.error(request, "Fill date, start time, end time and class.")
        return redirect("agendar_reposicao", presenca_id=presenca.id)

    return render(
        request,
        "accounts/form_reposicao.html",
        {
            "form_mode": "schedule",
            "presenca": presenca,
            "reposicao": None,
            "turmas": turmas,
        },
    )


@login_required
def editar_reposicao_agendada(request, reposicao_id):
    if not _pode_gerenciar_turma(request.user):
        return HttpResponseForbidden("Only Global Makers and board members can edit repositions.")
    r = get_object_or_404(
        ReposicaoAgendada.objects.select_related(
            "presenca",
            "presenca__lesson",
            "presenca__lesson__class_group",
            "presenca__matricula",
            "presenca__matricula__aluno",
            "presenca__matricula__aluno__user",
            "turma",
            "lesson",
        ),
        id=reposicao_id,
    )
    turmas = Turma.objects.all().order_by("name")

    if request.method == "POST":
        if request.POST.get("delete_reposicao_id"):
            pres = r.presenca
            r.delete()
            if pres.reposicao_pendente == 0:
                pres.reposicao_pendente = 1
            pres.reposicao = True
            pres.save()
            messages.success(request, "Scheduled reposition removed. Global Cityzen marked as pending again.")
            return redirect("lista_reposicoes")

        data_agendada = parse_date(request.POST.get("data_agendada"))
        horario_inicio_raw = request.POST.get("horario_inicio")
        horario_fim_raw = request.POST.get("horario_fim")
        turma_id = request.POST.get("turma_id")
        observacao = request.POST.get("observacao")
        turma = Turma.objects.filter(id=turma_id).first() or r.turma or r.presenca.lesson.class_group
        if data_agendada and horario_inicio_raw and horario_fim_raw and turma:
            horario_inicio = datetime.strptime(horario_inicio_raw, "%H:%M").time()
            horario_fim = datetime.strptime(horario_fim_raw, "%H:%M").time()
            old_lesson = r.lesson
            new_lesson, err = _resolve_makeup_lesson(
                turma, data_agendada, horario_inicio, horario_fim, current_lesson=old_lesson
            )
            if err:
                messages.error(request, err)
            else:
                r.data_agendada = data_agendada
                r.horario_inicio = horario_inicio
                r.horario_fim = horario_fim
                r.turma = turma
                r.lesson = new_lesson
                r.observacao = observacao or ""
                r.save()
                old_pk = old_lesson.pk if old_lesson else None
                if old_pk and old_pk != new_lesson.pk:
                    _delete_lesson_if_unused(Lesson.objects.filter(pk=old_pk).first())
                messages.success(request, "Reposition schedule updated.")
                return redirect("lista_reposicoes")
        else:
            messages.error(request, "Could not update: check date, times and class.")
        return redirect("editar_reposicao_agendada", reposicao_id=r.id)

    return render(
        request,
        "accounts/form_reposicao.html",
        {
            "form_mode": "edit",
            "presenca": r.presenca,
            "reposicao": r,
            "turmas": turmas,
        },
    )


@login_required
def perfil(request):
    perfil_obj, _ = Perfil.objects.get_or_create(user=request.user)
    if request.method == "POST":
        request.user.first_name = request.POST.get("first_name", request.user.first_name)
        request.user.last_name = request.POST.get("last_name", request.user.last_name)
        request.user.email = request.POST.get("email", request.user.email)
        request.user.username = request.user.email
        request.user.save()

        avatar_form = PerfilForm(request.POST, request.FILES, instance=perfil_obj)
        if avatar_form.is_valid():
            avatar_form.save()
        messages.success(request, "Profile updated.")
        return redirect("perfil")

    return render(request, "accounts/perfil.html", {"perfil": perfil_obj})


def _persist_gamification_upload(media_model, fk_field, fk_obj, uploaded):
    if not uploaded:
        return
    ct = (getattr(uploaded, "content_type", None) or "").lower()
    name = (getattr(uploaded, "name", None) or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    image_ext = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
    use_image = ct.startswith("image/") or ext in image_ext
    payload = {fk_field: fk_obj}
    if use_image:
        payload["imagem"] = uploaded
    else:
        payload["arquivo"] = uploaded
    media_model.objects.create(**payload)


@login_required
def gamification(request):
    if request.method == "POST" and _is_management_user(request.user) and request.POST.get("create_challenge"):
        form = GamificationChallengeForm(request.POST, request.FILES)
        if form.is_valid():
            challenge = form.save(commit=False)
            challenge.criado_por = request.user
            challenge.save()
            _persist_gamification_upload(
                GamificationChallengeMedia, "challenge", challenge, request.FILES.get("attachment")
            )
            if form.cleaned_data.get("video_url"):
                GamificationChallengeMedia.objects.create(challenge=challenge, video_url=form.cleaned_data["video_url"])
            messages.success(request, "Challenge created.")
            return redirect("gamification")

    sub_qs = GamificationSubmission.objects.select_related(
        "aluno", "aluno__user", "aluno__user__perfil"
    ).prefetch_related("midias")
    aluno_obj = Aluno.objects.filter(user=request.user).first()
    if is_aluno(request.user) and aluno_obj:
        sub_qs = sub_qs.filter(aluno=aluno_obj)
    sub_prefetch = Prefetch("submissoes", queryset=sub_qs)
    challenges = (
        GamificationChallenge.objects.select_related("criado_por", "criado_por__perfil")
        .prefetch_related("midias", sub_prefetch)
        .order_by("-criado_em")
    )
    for c in challenges:
        c.creator_avatar_url = _user_avatar_url(c.criado_por)
        if is_aluno(request.user):
            subs = list(c.submissoes.all())
            c.minha_submissao = subs[0] if subs else None
        else:
            c.minha_submissao = None
            for s in c.submissoes.all():
                s.student_avatar_url = _user_avatar_url(s.aluno.user)
    challenge_form = GamificationChallengeForm()

    if request.method == "POST" and is_aluno(request.user) and request.POST.get("challenge_id"):
        challenge = get_object_or_404(GamificationChallenge, id=request.POST["challenge_id"], ativo=True)
        sub, _ = GamificationSubmission.objects.get_or_create(challenge=challenge, aluno=aluno_obj)
        sub.comentario = request.POST.get("comentario")
        sub.save()
        _persist_gamification_upload(
            GamificationSubmissionMedia, "submission", sub, request.FILES.get("attachment")
        )
        video_url = request.POST.get("video_url")
        if video_url:
            GamificationSubmissionMedia.objects.create(submission=sub, video_url=video_url)
        messages.success(request, "Task submitted.")
        return redirect("gamification")

    if request.method == "POST" and _is_management_user(request.user) and request.POST.get("delete_challenge_id"):
        ch = get_object_or_404(GamificationChallenge, id=request.POST["delete_challenge_id"])
        ch.delete()
        messages.success(request, "Challenge deleted.")
        return redirect("gamification")

    if request.method == "POST" and _is_management_user(request.user) and request.POST.get("toggle_challenge_id"):
        ch = get_object_or_404(GamificationChallenge, id=request.POST["toggle_challenge_id"])
        ch.ativo = not ch.ativo
        ch.save()
        messages.success(request, "Challenge status updated.")
        return redirect("gamification")

    sub_all = GamificationSubmission.objects.select_related(
        "aluno", "aluno__user", "aluno__user__perfil", "challenge"
    )
    # Aluno só enxerga as PRÓPRIAS submissões (antes vinha tudo no contexto)
    if is_aluno(request.user) and aluno_obj:
        sub_all = sub_all.filter(aluno=aluno_obj)
    submissions = list(sub_all.order_by("-id")[:100])
    for s in submissions:
        s.student_avatar_url = _user_avatar_url(s.aluno.user)

    # Indicadores do topo — calculados em memória, sem query extra
    kpis = {
        "challenges_ativos": sum(1 for c in challenges if c.ativo),
        "challenges_total": len(challenges),
        "submissoes": len(submissions),
        "pendentes": sum(1 for s in submissions if not s.concluido),
        "pontos": sum((c.pontos or 0) for c in challenges if c.ativo),
        "meus_pontos": sum((s.challenge.pontos or 0) for s in submissions if s.concluido),
    }
    return render(request, "accounts/gamification.html", {
        "challenges": challenges,
        "challenge_form": challenge_form,
        "submissions": submissions,
        "kpis": kpis,
        "is_staff_user": _is_management_user(request.user),
        "is_student_user": is_aluno(request.user),
    })


@login_required
def ranking_gamification(request):
    ranking = (
        GamificationSubmission.objects.filter(concluido=True)
        .values("aluno__id", "aluno__user__first_name", "aluno__user__last_name")
        .annotate(pontos=Count("id"), total=Avg("challenge__pontos"))
        .order_by("-pontos", "-total")
    )
    return render(request, "accounts/ranking_gamification.html", {"ranking": ranking})


@login_required
def validar_gamification(request, submission_id):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()
    sub = get_object_or_404(GamificationSubmission, id=submission_id)
    sub.concluido = True
    sub.validado_por = request.user
    sub.validado_em = timezone.now()
    sub.save()
    messages.success(request, "Submission validated.")
    return redirect("gamification")


@login_required
def invalidar_gamification(request, submission_id):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()
    sub = get_object_or_404(GamificationSubmission, id=submission_id)
    sub.concluido = False
    sub.validado_por = None
    sub.validado_em = None
    sub.save()
    messages.success(request, "Validation revoked. Submission is pending again.")
    return redirect("gamification")


@login_required
def estrategias(request):
    is_staff = _is_management_user(request.user)
    is_student = is_aluno(request.user)

    if not is_staff and not is_student:
        return HttpResponseForbidden()

    acesso_prefetch = Prefetch(
        "acessos",
        queryset=EstrategiaAlunoAcesso.objects.select_related("aluno", "aluno__user"),
    )
    todas = list(Estrategia.objects.prefetch_related(acesso_prefetch))

    if is_student:
        aluno_obj = Aluno.objects.filter(user=request.user).first()
        if not aluno_obj:
            return HttpResponseForbidden()
        ids_liberados = set(
            EstrategiaAlunoAcesso.objects.filter(aluno=aluno_obj).values_list("estrategia_id", flat=True)
        )
        estrategias_list = [e for e in todas if e.id in ids_liberados]
    else:
        estrategias_list = todas

    return render(
        request,
        "accounts/estrategias.html",
        {
            "estrategias": estrategias_list,
            "is_staff_view": is_staff,
            "is_student_view": is_student,
        },
    )


@login_required
def gerenciar_acesso_estrategia(request, id):
    if not _is_management_user(request.user):
        return HttpResponseForbidden()

    estrategia = get_object_or_404(Estrategia, id=id)
    redirect_url = reverse("gerenciar_acesso_estrategia", args=[estrategia.id])

    if request.method == "POST":
        if request.POST.get("aluno_id"):
            aluno = get_object_or_404(Aluno, id=request.POST["aluno_id"])
            _, created = EstrategiaAlunoAcesso.objects.get_or_create(
                estrategia=estrategia,
                aluno=aluno,
                defaults={"liberado_por": request.user},
            )
            if created:
                messages.success(request, f"Access granted to {aluno.user.get_full_name()}.")
            else:
                messages.info(request, "This Global Cityzen already has access to this strategy.")
            return redirect(redirect_url)

        if request.POST.get("revoke_acesso_id"):
            acesso = get_object_or_404(
                EstrategiaAlunoAcesso,
                id=request.POST["revoke_acesso_id"],
                estrategia=estrategia,
            )
            nome = acesso.aluno.user.get_full_name()
            acesso.delete()
            messages.success(request, f"Access removed for {nome}.")
            return redirect(redirect_url)

    acessos = list(
        EstrategiaAlunoAcesso.objects.filter(estrategia=estrategia)
        .select_related("aluno", "aluno__user")
        .order_by("aluno__user__first_name", "aluno__user__last_name")
    )
    ids_com_acesso = {a.aluno_id for a in acessos}
    alunos_sem_acesso = list(
        Aluno.objects.filter(user__is_active=True)
        .exclude(id__in=ids_com_acesso)
        .select_related("user")
        .order_by("user__first_name", "user__last_name")
    )

    return render(
        request,
        "accounts/estrategia_acesso.html",
        {
            "estrategia": estrategia,
            "acessos": acessos,
            "alunos_sem_acesso": alunos_sem_acesso,
        },
    )


@login_required
@diretor_required
def editar_estrategia(request, id):
    estrategia = get_object_or_404(Estrategia, id=id)
    if request.method == "POST":
        form = EstrategiaForm(request.POST, request.FILES, instance=estrategia)
        if form.is_valid():
            form.save()
            messages.success(request, "Strategy materials updated.")
            return redirect("estrategias")
    else:
        form = EstrategiaForm(instance=estrategia)
    return render(
        request,
        "accounts/editar_estrategia.html",
        {"estrategia": estrategia, "form": form},
    )


@login_required
@diretor_required
def financeiro(request):
    qstr = urlencode(request.GET) if request.GET else ""
    redir = f"{reverse('financeiro')}?{qstr}" if qstr else reverse("financeiro")

    if request.method == "POST":
        if "save_entry" in request.POST:
            form_entry = FinancialEntryForm(request.POST)
            form_contract = ContractForm()
            if form_entry.is_valid():
                e = form_entry.save(commit=False)
                e.criado_por = request.user
                e.save()
                messages.success(request, "Financial entry saved.")
                return redirect(redir)
        else:
            form_contract = ContractForm(request.POST)
            form_entry = FinancialEntryForm()
            if form_contract.is_valid():
                form_contract.save()
                messages.success(request, "Contract saved.")
                return redirect(redir)
    else:
        form_entry = FinancialEntryForm()
        form_contract = ContractForm()

    entry_from = parse_date((request.GET.get("entry_from") or "").strip() or None) if (request.GET.get("entry_from") or "").strip() else None
    entry_to = parse_date((request.GET.get("entry_to") or "").strip() or None) if (request.GET.get("entry_to") or "").strip() else None
    entry_qs = FinancialEntry.objects.all().order_by("-data", "-id")
    if entry_from:
        entry_qs = entry_qs.filter(data__gte=entry_from)
    if entry_to:
        entry_qs = entry_qs.filter(data__lte=entry_to)
    entry_paginator = Paginator(entry_qs, 30)
    lancamentos = entry_paginator.get_page(request.GET.get("entries_page"))

    contract_filter = (request.GET.get("contract_filter") or "all").strip()
    contract_qs = Contract.objects.select_related("aluno", "aluno__user").order_by("-inicio", "-id")
    if contract_filter == "active":
        contract_qs = contract_qs.filter(ativo=True)
    elif contract_filter == "inactive":
        contract_qs = contract_qs.filter(ativo=False)
    contract_paginator = Paginator(contract_qs, 30)
    contratos = contract_paginator.get_page(request.GET.get("contracts_page"))

    monthly = (
        FinancialEntry.objects.annotate(mes=TruncMonth("data"))
        .values("mes", "tipo")
        .annotate(total=Sum("valor"))
        .order_by("mes")
    )
    month_map = {}
    for row in monthly:
        key = row["mes"].strftime("%m/%Y")
        if key not in month_map:
            month_map[key] = {"income": 0, "expense": 0}
        month_map[key][row["tipo"]] = float(row["total"] or 0)
    _union_contract_month_keys_into_map(month_map)
    _apply_contract_income_to_month_map(month_map)
    ml, mi, me = _finance_chart_series_last_n(month_map, 12)
    return render(request, "accounts/financeiro.html", {
        "form_entry": form_entry,
        "form_contract": form_contract,
        "lancamentos": lancamentos,
        "contratos": contratos,
        "monthly": monthly,
        "monthly_labels": json.dumps(ml),
        "monthly_income": json.dumps(mi),
        "monthly_expense": json.dumps(me),
        "entry_from_value": request.GET.get("entry_from", ""),
        "entry_to_value": request.GET.get("entry_to", ""),
        "contract_filter": contract_filter,
        "entries_total": entry_qs.count(),
        "contracts_total": contract_qs.count(),
    })


@login_required
@diretor_required
def financeiro_dashboard(request):
    today = timezone.now().date()
    df_s = (request.GET.get("date_from") or "").strip()
    dt_s = (request.GET.get("date_to") or "").strip()
    date_from_d = parse_date(df_s) if df_s else None
    date_to_d = parse_date(dt_s) if dt_s else None
    use_custom_range = bool(date_from_d and date_to_d and date_from_d <= date_to_d)

    if use_custom_range:
        period_start, period_end = date_from_d, date_to_d
    else:
        period_start = date(today.year, today.month, 1)
        period_end = today

    entries = (
        FinancialEntry.objects.filter(data__gte=period_start, data__lte=period_end)
        .select_related("criado_por")
        .order_by("-data", "-id")
    )
    contract_qs = _contracts_overlapping_period(period_start, period_end)
    contract_month_total = contract_qs.aggregate(s=Sum("valor_mensal"))["s"] or 0
    total_entry_income = entries.filter(tipo="income").aggregate(s=Sum("valor"))["s"] or 0
    total_expense = entries.filter(tipo="expense").aggregate(s=Sum("valor"))["s"] or 0
    total_income = float(total_entry_income or 0) + float(contract_month_total or 0)
    net = total_income - float(total_expense or 0)

    ledger_rows = []
    for e in entries:
        ledger_rows.append(
            {
                "data": e.data,
                "descricao": e.descricao,
                "tipo": e.tipo,
                "valor": e.valor,
                "is_contract": False,
            }
        )
    for c in contract_qs:
        ledger_rows.append(
            {
                "data": max(c.inicio, period_start),
                "descricao": f"Contract — {c.aluno.user.get_full_name() or c.aluno.user.username}",
                "tipo": "income",
                "valor": c.valor_mensal,
                "is_contract": True,
            }
        )
    ledger_rows.sort(key=lambda r: (r["data"], r.get("is_contract", False)), reverse=True)

    monthly = (
        FinancialEntry.objects.annotate(mes=TruncMonth("data"))
        .values("mes", "tipo")
        .annotate(total=Sum("valor"))
        .order_by("mes")
    )
    month_map = {}
    for row in monthly:
        key = row["mes"].strftime("%m/%Y")
        if key not in month_map:
            month_map[key] = {"income": 0, "expense": 0}
        month_map[key][row["tipo"]] = float(row["total"] or 0)
    _union_contract_month_keys_into_map(month_map)
    _apply_contract_income_to_month_map(month_map)
    if use_custom_range:
        ml, mi, me = _finance_chart_for_custom_range(month_map, period_start, period_end)
    else:
        ml, mi, me = _finance_chart_series_last_n(month_map, 12)
    return render(request, "accounts/financeiro_dashboard.html", {
        "monthly_labels": json.dumps(ml),
        "monthly_income": json.dumps(mi),
        "monthly_expense": json.dumps(me),
        "ledger_rows": ledger_rows,
        "total_income": total_income,
        "total_expense": total_expense,
        "net": net,
        "period_start": period_start,
        "period_end": period_end,
        "date_from_value": df_s,
        "date_to_value": dt_s,
        "balance_is_custom_range": use_custom_range,
    })


@login_required
def student_dashboard(request):
    aluno = get_object_or_404(Aluno, user=request.user)
    ctx = _student_dashboard_chart_context(aluno)
    ctx["aluno"] = aluno
    return render(request, "accounts/student_dashboard.html", ctx)

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