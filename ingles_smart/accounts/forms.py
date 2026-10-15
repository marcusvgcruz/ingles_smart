import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.models import User
from .models import Perfil
from academico.models import (
    Aluno, Professor, Turma, TurmaHorario, Matricula, TimeBlock, BlockedPeriod, ScheduleTemplate,
    Nivel,
)
from onboarding.models import OnboardingItem
from gamificacao.models import GamificationChallenge, GamificationSubmission
from financeiro.models import FinancialEntry, Contract
from estrategias.models import Estrategia
from django.core.exceptions import ValidationError
from avaliacoes.models import Competencia
from feed.models import Post

class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    widget = MultiFileInput

    def clean(self, data, initial=None):
        if isinstance(data, (list, tuple)):
            return [super().clean(d, initial) for d in data]
        return super().clean(data, initial)

class CustomUserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get("first_name")
        last_name = cleaned_data.get("last_name")

        if not first_name:
            self.add_error("first_name", "First name is required.")

        if not last_name:
            self.add_error("last_name", "Last name is required.")

        return cleaned_data

class EsqueciSenhaForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(
            attrs={
                "class": "login-input",
                "placeholder": "Your registered email",
                "autocomplete": "email",
            }
        ),
    )


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'class': 'login-input',
            'placeholder': 'Email'
        })
    )

    password = forms.CharField(
        label="",
        widget=forms.PasswordInput(attrs={
            'class': 'login-input',
            'placeholder': 'Password'
        })
    )

class NivelForm(forms.ModelForm):

    class Meta:
        model = Nivel
        fields = ["nome", "ordem", "ativo"]

        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "ordem": forms.NumberInput(attrs={"class": "form-control"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-checkbox"})
        }

class AvaliacaoForm(forms.Form):

    aluno = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.HiddenInput()
    )

    observacoes = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label="Notes"
    )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        competencias = Competencia.objects.filter(ativa=True)

        for competencia in competencias:

            self.fields[f"competencia_{competencia.id}"] = forms.ChoiceField(
                choices = [
                    (n.id, n.nome)
                    for n in Nivel.objects.filter(ativo=True)
                ],
                label=competencia.nome,
                widget=forms.Select(attrs={"class": "form-control"})
            )

class CompetenciaForm(forms.ModelForm):

    class Meta:
        model = Competencia
        fields = ["nome", "ordem", "ativa"]

        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "ordem": forms.NumberInput(attrs={"class": "form-control"}),
            "ativa": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

class AlunoForm(forms.ModelForm):
    nome = forms.CharField(max_length=150)
    sobrenome = forms.CharField(max_length=150)
    email = forms.EmailField()
    data_nascimento = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Aluno
        fields = ["cpf", "telefone", "endereco", "data_nascimento", "tipo"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-control"}),
        }
    

    def clean_email(self):
        email = self.cleaned_data.get("email")

        qs = User.objects.filter(username=email)

        if self.instance.id:
            qs = qs.exclude(id=self.instance.user.id)

        if qs.exists():
            raise ValidationError("A user with this email already exists.")

        return email
    
    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")

        # Remove tudo que não for número
        cpf = re.sub(r'\D', '', cpf)

        if len(cpf) != 11:
            raise ValidationError("CPF must contain 11 digits.")

        return cpf
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.id:
            # Preencher campos do User
            self.initial['nome'] = self.instance.user.first_name
            self.initial['sobrenome'] = self.instance.user.last_name
            self.initial['email'] = self.instance.user.email

            # Formatar CPF
            cpf = self.instance.cpf
            if cpf and len(cpf) == 11:
                self.initial['cpf'] = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    def save(self, commit=True):
        aluno = super().save(commit=False)
        if aluno.user_id:
            user = aluno.user
            user.first_name = self.cleaned_data["nome"]
            user.last_name = self.cleaned_data["sobrenome"]
            user.email = self.cleaned_data["email"]
            user.username = self.cleaned_data["email"]
            user.save()
        if commit:
            aluno.save()
        return aluno


class ProfessorForm(forms.ModelForm):
    nome = forms.CharField(max_length=150)
    sobrenome = forms.CharField(max_length=150)
    email = forms.EmailField()
    data_nascimento = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Professor
        fields = ['cpf', 'telefone', 'endereco', 'data_nascimento']

    def clean_email(self):
        email = self.cleaned_data.get("email")

        qs = User.objects.filter(username=email)

        if self.instance.id:
            qs = qs.exclude(id=self.instance.user.id)

        if qs.exists():
            raise ValidationError("A user with this email already exists.")

        return email
    
    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")

        # Remove tudo que não for número
        cpf = re.sub(r'\D', '', cpf)

        if len(cpf) != 11:
            raise ValidationError("CPF must contain 11 digits.")

        return cpf
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.id:
            # Preencher campos do User
            self.initial['nome'] = self.instance.user.first_name
            self.initial['sobrenome'] = self.instance.user.last_name
            self.initial['email'] = self.instance.user.email

            # Formatar CPF
            cpf = self.instance.cpf
            if cpf and len(cpf) == 11:
                self.initial['cpf'] = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    def save(self, commit=True):
        professor = super().save(commit=False)
        if professor.user_id:
            user = professor.user
            user.first_name = self.cleaned_data["nome"]
            user.last_name = self.cleaned_data["sobrenome"]
            user.email = self.cleaned_data["email"]
            user.username = self.cleaned_data["email"]
            user.save()
        if commit:
            professor.save()
        return professor


class ScheduleTemplateForm(forms.ModelForm):

    class Meta:
        model = ScheduleTemplate
        fields = ["name", "active"]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Template name"
            }),
            "active": forms.CheckboxInput(attrs={
                "class": "form-checkbox"
            })
        }


class TurmaForm(forms.ModelForm):

    class Meta:
        model = Turma
        fields = [
            "name",
            "room",
            "time_blocks"
            ]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "time_blocks": forms.SelectMultiple(attrs={"class": "form-control select2", "size": 12})
        }


class MatriculaForm(forms.ModelForm):

    class Meta:
        model = Matricula
        fields = ["turma", "data_inicio", "data_fim"]

        widgets = {
            "turma": forms.Select(attrs={"class": "form-control select2"}),
            "data_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "data_fim": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

class TimeBlockForm(forms.ModelForm):

    class Meta:
        model = TimeBlock
        fields = ["weekday", "start_time", "end_time"]

        widgets = {
            "weekday": forms.Select(attrs={"class": "form-control"}),
            "start_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "end_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if start_time and end_time:
            duration = (
                end_time.hour * 60 + end_time.minute
            ) - (
                start_time.hour * 60 + start_time.minute
            )
            if duration != 40:
                raise ValidationError("Each class block must be exactly 40 minutes.")
        return cleaned_data


class BlockedPeriodForm(forms.ModelForm):

    class Meta:
        model = BlockedPeriod
        fields = ["name", "start_date", "end_date"]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

class PostForm(forms.ModelForm):
    """Anexos vêm de inputs HTML e são salvos na view (request.FILES.getlist)."""

    conteudo = forms.CharField(required=False)

    class Meta:
        model = Post
        fields = ['conteudo']


class OnboardingItemForm(forms.ModelForm):
    class Meta:
        model = OnboardingItem
        fields = ["nome", "ordem", "ativo"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "ordem": forms.NumberInput(attrs={"class": "form-control"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ["avatar"]


class GamificationChallengeForm(forms.ModelForm):
    video_url = forms.URLField(required=False, widget=forms.URLInput(attrs={"class": "form-control", "placeholder": "Video URL (optional)"}))

    class Meta:
        model = GamificationChallenge
        fields = ["titulo", "descricao", "pontos", "ativo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "pontos": forms.NumberInput(attrs={"class": "form-control"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class GamificationSubmissionForm(forms.ModelForm):
    class Meta:
        model = GamificationSubmission
        fields = ["comentario"]
        widgets = {
            "comentario": forms.TextInput(attrs={"class": "form-control", "placeholder": "Comment"}),
        }


_ESTRATEGIA_AUDIO_WIDGET = forms.FileInput(attrs={"class": "form-control", "accept": "audio/*,.mp3"})


class EstrategiaForm(forms.ModelForm):
    class Meta:
        model = Estrategia
        fields = [
            "titulo",
            "descricao",
            "pdf_portugues",
            "pdf_ingles",
            "study_sesh_portuguese",
            "study_sesh_english",
            "strategy_portuguese",
            "strategy_brazilian_english",
            "strategy_irish_english",
            "strategy_australian_english",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "pdf_portugues": forms.FileInput(attrs={"class": "form-control", "accept": ".pdf"}),
            "pdf_ingles": forms.FileInput(attrs={"class": "form-control", "accept": ".pdf"}),
            "study_sesh_portuguese": _ESTRATEGIA_AUDIO_WIDGET,
            "study_sesh_english": _ESTRATEGIA_AUDIO_WIDGET,
            "strategy_portuguese": _ESTRATEGIA_AUDIO_WIDGET,
            "strategy_brazilian_english": _ESTRATEGIA_AUDIO_WIDGET,
            "strategy_irish_english": _ESTRATEGIA_AUDIO_WIDGET,
            "strategy_australian_english": _ESTRATEGIA_AUDIO_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        if instance:
            for field_name, label in instance.audio_field_labels():
                self.fields[field_name].label = label
        self.fields["pdf_portugues"].label = "PDF (Portuguese)"
        self.fields["pdf_ingles"].label = "PDF (English)"


class FinancialEntryForm(forms.ModelForm):
    class Meta:
        model = FinancialEntry
        fields = ["descricao", "tipo", "valor", "data"]
        widgets = {
            "descricao": forms.TextInput(attrs={"class": "form-control"}),
            "tipo": forms.Select(attrs={"class": "form-control"}),
            "valor": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "data": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ["aluno", "valor_mensal", "ativo", "inicio", "fim", "observacao"]
        widgets = {
            "aluno": forms.Select(attrs={"class": "form-control select2"}),
            "valor_mensal": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fim": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "observacao": forms.TextInput(attrs={"class": "form-control"}),
        }