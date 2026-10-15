from django.contrib import admin
from academico.models import Turma, Presenca, Lesson
from avaliacoes.models import Competencia, Avaliacao, NotaCompetencia
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm
from datetime import timedelta, date
from django.utils import timezone
from django.contrib import messages
from academico.models import Turma, Lesson, BlockedPeriod, ScheduleTemplate, TimeBlock, Room

admin.site.register(Presenca)
admin.site.register(Competencia)
admin.site.register(Avaliacao)
admin.site.register(NotaCompetencia)
admin.site.register(Room)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("class_group", "date", "start_time", "end_time")

class CustomUserAdmin(UserAdmin):
    form = CustomUserCreationForm

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

from academico.models import BlockedPeriod

@admin.register(BlockedPeriod)
class BlockedPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")


class PresencaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'data', 'presente', 'professor')

    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.professor = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request, obj=None):
        return request.user.groups.filter(name='Professores').exists()
# Register your models here.

def generate_lessons(modeladmin, request, queryset):
    today = timezone.now().date()
    end_of_year = date(today.year, 12, 31)

    for turma in queryset:
        time_blocks = turma.time_blocks.all()

        if not time_blocks:
            messages.error(request, f"Class {turma} has no schedule defined.")
            continue

        current_date = today

        while current_date <= end_of_year:

            for block in time_blocks:

                if current_date.weekday() == block.weekday:

                    is_blocked = BlockedPeriod.objects.filter(
                        start_date__lte=current_date,
                        end_date__gte=current_date
                    ).exists()

                    if not is_blocked:

                        Lesson.objects.get_or_create(
                            class_group=turma,
                            date=current_date,
                            start_time=block.start_time,
                            end_time=block.end_time
                        )

            current_date += timedelta(days=1)

    messages.success(request, "Lessons generated successfully.")

generate_lessons.short_description = "Generate Lessons"

@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("name", "room")
    filter_horizontal = ("time_blocks",)
    actions = [generate_lessons]

@admin.register(ScheduleTemplate)
class ScheduleTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "active", "created_at")


@admin.register(TimeBlock)
class TimeBlockAdmin(admin.ModelAdmin):
    list_display = ("template", "weekday", "start_time", "end_time")
