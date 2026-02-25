from django import forms
from django.contrib.auth.models import User
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