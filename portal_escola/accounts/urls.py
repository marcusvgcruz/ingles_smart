from django.urls import path
from . import views

from .views import CustomLoginView
from django.contrib.auth.views import LogoutView

from .views import (
    lista_alunos,
    desativar_aluno,
    reativar_aluno,
    dashboard,
    lista_professores,
    desativar_professor,
    reativar_professor,
)

urlpatterns = [
    # Auth / portal
    path("login/", CustomLoginView.as_view(), name="login"),
    path("trocar-senha/", views.trocar_senha, name="trocar_senha"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # Professor altera a senha
    path("resetar-senha/<int:user_id>/", views.resetar_senha, name="resetar_senha"),
    

    path('dashboard/', dashboard, name='dashboard'),
    path("feed/", views.feed, name="feed"),

    path("avaliacao/nova/", views.nova_avaliacao, name="nova_avaliacao"),

    # Presença
    path('turma/<int:turma_id>/presenca/', views.marcar_presenca, name='marcar_presenca'),

    # Alunos
    path("alunos/", lista_alunos, name="lista_alunos"),

    path('alunos/<int:id>/', views.detalhe_aluno, name='detalhe_aluno'),

    path("alunos/desativar/<int:user_id>/", desativar_aluno, name="desativar_aluno"),

    path("alunos/reativar/<int:user_id>/", reativar_aluno, name="reativar_aluno"),
    
    path('alunos/novo/', views.criar_aluno, name='criar_aluno'),

    # Professores
    path("professores/", lista_professores, name="lista_professores"),
    path("professores/desativar/<int:user_id>/", desativar_professor, name="desativar_professor"),
    path("professores/reativar/<int:user_id>/", reativar_professor, name="reativar_professor"),
    path('professores/novo/', views.criar_professor, name='criar_professor'),

]

