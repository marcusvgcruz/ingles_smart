import re
from django import forms
from django.contrib.auth.models import User
from .models import Aluno
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

        if User.objects.filter(username=email).exists():
            raise ValidationError("Já existe usuário com esse e-mail.")

        return email
    
    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")

        # Remove tudo que não for número
        cpf = re.sub(r'\D', '', cpf)

        if len(cpf) != 11:
            raise ValidationError("CPF deve conter 11 dígitos.")

        return cpf