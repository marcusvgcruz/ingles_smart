import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.models import User
from .models import Aluno, Professor, Turma, TurmaHorario, Matricula, TimeBlock, BlockedPeriod
from django.core.exceptions import ValidationError
from .models import Competencia, NIVEIS

class CustomUserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get("first_name")
        last_name = cleaned_data.get("last_name")

        if not first_name:
            self.add_error("first_name", "O nome é obrigatório.")

        if not last_name:
            self.add_error("last_name", "O sobrenome é obrigatório.")

        return cleaned_data

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'class': 'login-input',
            'placeholder': 'E-mail'
        })
    )

    password = forms.CharField(
        label="",
        widget=forms.PasswordInput(attrs={
            'class': 'login-input',
            'placeholder': 'Senha'
        })
    )

class AvaliacaoForm(forms.Form):
    aluno = forms.ModelChoiceField(
        queryset=User.objects.filter(
            groups__name="Alunos",
            is_active = True
        ),
        label="Aluno"
    )

    observacoes = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label="Observações"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        competencias = Competencia.objects.filter(ativa=True)

        for competencia in competencias:
            self.fields[f"competencia_{competencia.id}"] = forms.ChoiceField(
                choices=NIVEIS,
                label=competencia.nome
            )

class AlunoForm(forms.ModelForm):
    nome = forms.CharField(max_length=150)
    sobrenome = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = Aluno
        fields = ['cpf', 'telefone', 'endereco']

    def clean_email(self):
        email = self.cleaned_data.get("email")

        qs = User.objects.filter(username=email)

        if self.instance.id:
            qs = qs.exclude(id=self.instance.user.id)

        if qs.exists():
            raise ValidationError("Já existe usuário com esse e-mail.")

        return email
    
    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")

        # Remove tudo que não for número
        cpf = re.sub(r'\D', '', cpf)

        if len(cpf) != 11:
            raise ValidationError("CPF deve conter 11 dígitos.")

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
    
    
class ProfessorForm(forms.ModelForm):
    nome = forms.CharField(max_length=150)
    sobrenome = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = Professor
        fields = ['cpf', 'telefone', 'endereco']

    def clean_email(self):
        email = self.cleaned_data.get("email")

        qs = User.objects.filter(username=email)

        if self.instance.id:
            qs = qs.exclude(id=self.instance.user.id)

        if qs.exists():
            raise ValidationError("Já existe usuário com esse e-mail.")

        return email
    
    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")

        # Remove tudo que não for número
        cpf = re.sub(r'\D', '', cpf)

        if len(cpf) != 11:
            raise ValidationError("CPF deve conter 11 dígitos.")

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
    



class TurmaForm(forms.ModelForm):

    class Meta:
        model = Turma
        fields = [
            "name",
            "room",
            "start_date",
            "end_date",
            "time_blocks"
            ]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),

            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),

            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),

            "time_blocks": forms.CheckboxSelectMultiple()
        }

    
    

class MatriculaForm(forms.ModelForm):

    class Meta:
        model = Matricula
        fields = ["turma", "data_inicio", "data_fim"]

        widgets = {
            "aluno": forms.Select(attrs={"class": "form-control select2"}),
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


class BlockedPeriodForm(forms.ModelForm):

    class Meta:
        model = BlockedPeriod
        fields = ["name", "start_date", "end_date"]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }