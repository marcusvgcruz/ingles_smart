from django.contrib import admin
from .models import Turma, Aula, Presenca, Competencia, Avaliacao, NotaCompetencia
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm

admin.site.register(Turma)
admin.site.register(Aula)
admin.site.register(Presenca)
admin.site.register(Competencia)
admin.site.register(Avaliacao)
admin.site.register(NotaCompetencia)

class CustomUserAdmin(UserAdmin):
    form = CustomUserCreationForm

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)




class PresencaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'data', 'presente', 'professor')

    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.professor = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request, obj=None):
        return request.user.groups.filter(name='Professores').exists()
# Register your models here.
