from django import forms
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from .models import Usuario, Grupo


class PerfilUsuarioForm(UserChangeForm):
    password = None
    
    # Campos readonly para mostrar grupos
    grupo_primario_display = forms.CharField(
        label='Setor Principal',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True})
    )
    grupos_secundarios_display = forms.CharField(
        label='Setores Secundários',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'readonly': True, 'rows': 2})
    )
    
    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'telefone')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
        }
        labels = {
            'username': 'Nome de Usuário',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
            'telefone': 'Telefone',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Preenche os campos de grupo para exibição
            try:
                if hasattr(self.instance, 'grupo_primario') and self.instance.grupo_primario:
                    self.fields['grupo_primario_display'].initial = self.instance.grupo_primario.get_hierarquia_completa()
                else:
                    self.fields['grupo_primario_display'].initial = 'Não definido'
                
                if hasattr(self.instance, 'grupos_secundarios'):
                    grupos_sec = self.instance.grupos_secundarios.all()
                    if grupos_sec:
                        grupos_text = ', '.join([g.get_hierarquia_completa() for g in grupos_sec])
                        self.fields['grupos_secundarios_display'].initial = grupos_text
                    else:
                        self.fields['grupos_secundarios_display'].initial = 'Nenhum setor secundário'
            except:
                # Se ainda não há migrações aplicadas, campos podem não existir
                self.fields['grupo_primario_display'].initial = 'Não definido'
                self.fields['grupos_secundarios_display'].initial = 'Nenhum setor secundário'


class AlterarSenhaForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Senha Atual',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        label='Nova Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        label='Confirmar Nova Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


class UsuarioCreateForm(forms.ModelForm):
    """Formulário para criação de usuários com validação de grupos."""
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'telefone', 'grupo_primario', 'grupos_secundarios')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'grupo_primario': forms.Select(attrs={'class': 'form-control'}),
            'grupos_secundarios': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra apenas grupos ativos
        try:
            self.fields['grupo_primario'].queryset = Grupo.objects.filter(ativo=True)
            self.fields['grupos_secundarios'].queryset = Grupo.objects.filter(ativo=True)
        except:
            # Se ainda não há migrações aplicadas
            pass
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('As senhas não coincidem.')
        return password2
    
    def clean_grupo_primario(self):
        grupo_primario = self.cleaned_data.get('grupo_primario')
        if not grupo_primario:
            raise ValidationError('Usuário deve ter um setor principal definido.')
        if not grupo_primario.ativo:
            raise ValidationError('O setor principal deve estar ativo.')
        return grupo_primario
    
    def clean_grupos_secundarios(self):
        grupos_secundarios = self.cleaned_data.get('grupos_secundarios')
        if grupos_secundarios:
            for grupo in grupos_secundarios:
                if not grupo.ativo:
                    raise ValidationError(f'O setor "{grupo.nome}" deve estar ativo.')
        return grupos_secundarios
    
    def clean(self):
        cleaned_data = super().clean()
        grupo_primario = cleaned_data.get('grupo_primario')
        grupos_secundarios = cleaned_data.get('grupos_secundarios', [])
        
        # Validação para evitar duplicação entre setor principal e secundários
        if grupo_primario and grupos_secundarios:
            if grupo_primario in grupos_secundarios:
                raise ValidationError({
                    'grupos_secundarios': f'O setor "{grupo_primario.nome}" já está selecionado como principal. '
                                          'Não pode ser selecionado também nos setores secundários.'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            self.save_m2m()
        return user