from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views
from .views import CustomLoginView

urlpatterns = [

    # Acessos
    path("login/", CustomLoginView.as_view(), name="login"),
    path("trocar-senha/", views.trocar_senha, name="trocar_senha"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("resetar-senha/<int:user_id>/", views.resetar_senha, name="resetar_senha"),
    path("resetar-senha-professor/<int:user_id>/", views.resetar_senha_professor, name="resetar_senha_professor"),


    # Telas 
    path("dashboard/", views.dashboard, name="dashboard"),
    path("feed/", views.feed, name="feed"),
    path('post/<int:post_id>/delete/', views.deletar_post, name='deletar_post'),
    path('post/<int:post_id>/edit/', views.editar_post, name='editar_post'),
    path('post/<int:post_id>/fixar/', views.fixar_post, name='fixar_post'),
    path('post/<int:post_id>/desfixar/', views.desfazer_fixo, name='desfixar_post'),

    path("avaliacao/nova/", views.nova_avaliacao, name="nova_avaliacao"),
    path("avaliacao/aluno/<int:aluno_id>/", views.avaliacoes_aluno, name="avaliacoes_aluno"),

     # Competências
    path("competencias/", views.lista_competencias, name="lista_competencias"),
    path("competencias/nova/", views.nova_competencia, name="nova_competencia"),
    path("competencias/<int:id>/editar/", views.editar_competencia, name="editar_competencia"),
    path("niveis/criar/", views.criar_nivel, name="criar_nivel"),
    path("niveis/<int:id>/editar/", views.editar_nivel, name="editar_nivel"),

    # Matricula
    path("matriculas/nova/", views.criar_matricula, name="criar_matricula"),
    path("matriculas/", views.lista_matriculas, name="lista_matriculas"),
    path("matriculas/<int:matricula_id>/editar/", views.editar_matricula, name="editar_matricula"),
    path(
    "matriculas/<int:matricula_id>/finish/",
    views.finalizar_matricula,
    name="finalizar_matricula"
    ),

    # Agenda
    path("agenda/", views.agenda_mes, name="agenda_mes"),
    path(
    "agenda/<int:year>/<int:month>/<int:day>/",
    views.agenda_dia,
    name="agenda_dia"
    ),

    # Lessons
    path(
    "lesson/<int:lesson_id>/",
    views.lesson_detail,
    name="lesson_detail"
    ),
    path(
    "turmas/<int:turma_id>/gerar-lessons/",
    views.gerar_lessons,
    name="gerar_lessons"
    ),

    # Turmas
    path("turmas/", views.lista_turmas, name="lista_turmas"),
    path(
    "turmas/<int:turma_id>/",
    views.detalhe_turma,
    name="detalhe_turma"
    ),
    path("turmas/new/", views.criar_turma, name="criar_turma"),
    path("turmas/<int:turma_id>/editar/", views.editar_turma, name="editar_turma"),
    path("lesson/<int:lesson_id>/presenca/", views.marcar_presenca_lesson, name="marcar_presenca_lesson"),
    path("turmas/<int:turma_id>/calendar/", views.turma_calendar, name="turma_calendar"),

    # Alunos
    path("alunos/", views.lista_alunos, name="lista_alunos"),
    path("alunos/<int:id>/", views.detalhe_aluno, name="detalhe_aluno"),
    path("alunos/desativar/<int:user_id>/", views.desativar_aluno, name="desativar_aluno"),
    path("alunos/reativar/<int:user_id>/", views.reativar_aluno, name="reativar_aluno"),
    path("alunos/novo/", views.criar_aluno, name="criar_aluno"),

    # Professores
    path("professores/", views.lista_professores, name="lista_professores"),
    path("professores/<int:id>/", views.detalhe_professor, name="detalhe_professor"),
    path("professores/desativar/<int:user_id>/", views.desativar_professor, name="desativar_professor"),
    path("professores/reativar/<int:user_id>/", views.reativar_professor, name="reativar_professor"),
    path("professores/novo/", views.criar_professor, name="criar_professor"),
    path(
    "professores/<int:user_id>/promover/",
    views.promover_coordenador,
    name="promover_coordenador"
    ),

    # Templates
    path("templates/", views.lista_templates, name="lista_templates"),
    path("templates/<int:id>/", views.detalhe_template, name="detalhe_template"),
    path("templates/<int:id>/add-block/", views.add_timeblock, name="add_timeblock"),
    path("timeblock/<int:id>/edit/", views.editar_timeblock, name="editar_timeblock"),
    path("timeblock/<int:id>/delete/", views.delete_timeblock, name="delete_timeblock"),
    path("templates/new/", views.criar_template, name="criar_template"),

    # Blocked Periods
    path("blocked-periods/", views.lista_blocked_periods, name="lista_blocked_periods"),
    path("blocked-periods/new/", views.criar_blocked_period, name="criar_blocked_period"),
    path("blocked-periods/<int:id>/delete/", views.delete_blocked_period, name="delete_blocked_period"),

   

]
