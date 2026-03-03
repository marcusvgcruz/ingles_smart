from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views
from .views import CustomLoginView

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("trocar-senha/", views.trocar_senha, name="trocar_senha"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("resetar-senha/<int:user_id>/", views.resetar_senha, name="resetar_senha"),
    path("resetar-senha-professor/<int:user_id>/", views.resetar_senha_professor, name="resetar_senha_professor"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("feed/", views.feed, name="feed"),
    path("avaliacao/nova/", views.nova_avaliacao, name="nova_avaliacao"),
    path("avaliacoes/aluno/<int:aluno_id>/", views.avaliacoes_aluno, name="avaliacoes_aluno"),
    path("turmas/", views.lista_turmas, name="lista_turmas"),
    path("turmas/nova/", views.criar_turma, name="criar_turma"),
    path("turmas/<int:turma_id>/editar/", views.editar_turma, name="editar_turma"),
    path("turmas/<int:turma_id>/vinculo-manual/", views.vinculo_manual_turma, name="vinculo_manual_turma"),
    path("turmas/vinculo/<int:vinculo_id>/remover/", views.remover_vinculo_turma, name="remover_vinculo_turma"),
    path("turma/horario/<int:turma_horario_id>/presenca/", views.marcar_presenca, name="marcar_presenca"),
    path("alunos/", views.lista_alunos, name="lista_alunos"),
    path("alunos/<int:id>/", views.detalhe_aluno, name="detalhe_aluno"),
    path("alunos/desativar/<int:user_id>/", views.desativar_aluno, name="desativar_aluno"),
    path("alunos/reativar/<int:user_id>/", views.reativar_aluno, name="reativar_aluno"),
    path("alunos/novo/", views.criar_aluno, name="criar_aluno"),
    path("professores/", views.lista_professores, name="lista_professores"),
    path("professores/<int:id>/", views.detalhe_professor, name="detalhe_professor"),
    path("professores/desativar/<int:user_id>/", views.desativar_professor, name="desativar_professor"),
    path("professores/reativar/<int:user_id>/", views.reativar_professor, name="reativar_professor"),
    path("professores/novo/", views.criar_professor, name="criar_professor"),
]
