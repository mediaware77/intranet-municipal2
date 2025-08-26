from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django import forms
from .models import Usuario, Grupo


class UsuarioAdminForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        grupo_primario = cleaned_data.get('grupo_primario')
        grupos_secundarios = cleaned_data.get('grupos_secundarios', [])
        
        if not grupo_primario:
            raise ValidationError('Usuário deve ter um setor principal definido.')
        
        if grupo_primario and not grupo_primario.ativo:
            raise ValidationError('O setor principal deve estar ativo.')
        
        # Validação para evitar duplicação entre setor principal e secundários
        if grupo_primario and grupos_secundarios:
            if grupo_primario in grupos_secundarios:
                raise ValidationError({
                    'grupos_secundarios': f'O setor "{grupo_primario.nome}" já está definido como principal. '
                                          'Não pode ser selecionado também como secundário.'
                })
        
        return cleaned_data


class GrupoAdminForm(forms.ModelForm):
    class Meta:
        model = Grupo
        fields = '__all__'

    def clean_grupo_pai(self):
        grupo_pai = self.cleaned_data.get('grupo_pai')
        if grupo_pai and self.instance.pk:
            if grupo_pai == self.instance:
                raise ValidationError('Um grupo não pode ser pai de si mesmo.')
            
            if self.instance in grupo_pai.get_todos_subgrupos():
                raise ValidationError('Não é possível definir um subgrupo como pai.')
        return grupo_pai


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    form = GrupoAdminForm
    list_display = ('exibir_hierarquia', 'nome', 'grupo_pai', 'ativo', 'exibir_usuarios_primarios', 'exibir_usuarios_secundarios', 'data_criacao')
    list_filter = ('ativo', 'data_criacao', 'grupo_pai')
    search_fields = ('nome', 'descricao', 'grupo_pai__nome')
    list_editable = ('ativo',)
    readonly_fields = ('data_criacao', 'data_atualizacao', 'exibir_hierarquia_completa', 'exibir_nivel')
    ordering = ('nome',)
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao', 'grupo_pai', 'ativo')
        }),
        ('Informações da Hierarquia', {
            'fields': ('exibir_hierarquia_completa', 'exibir_nivel'),
            'classes': ('collapse',)
        }),
        ('Informações de Sistema', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

    def exibir_hierarquia(self, obj):
        """Exibe a hierarquia com indentação visual."""
        nivel = obj.get_nivel_hierarquia()
        indentacao = '—' * nivel
        return f"{indentacao} {obj.nome}" if nivel > 0 else obj.nome
    exibir_hierarquia.short_description = 'Hierarquia'

    def exibir_hierarquia_completa(self, obj):
        """Exibe o caminho completo da hierarquia."""
        return obj.get_hierarquia_completa()
    exibir_hierarquia_completa.short_description = 'Caminho Completo'

    def exibir_nivel(self, obj):
        """Exibe o nível na hierarquia."""
        return obj.get_nivel_hierarquia()
    exibir_nivel.short_description = 'Nível na Hierarquia'

    def get_queryset(self, request):
        """Otimiza consultas incluindo grupo_pai."""
        return super().get_queryset(request).select_related('grupo_pai')
    
    def has_module_permission(self, request):
        """Permite acesso ao módulo apenas para staff."""
        return request.user.is_staff
    
    def exibir_usuarios_primarios(self, obj):
        """Exibe a quantidade de usuários no setor principal."""
        count = obj.get_usuarios_primarios_count()
        return f"{count} usuário{'s' if count != 1 else ''}"
    exibir_usuarios_primarios.short_description = 'Setor Principal'
    
    def exibir_usuarios_secundarios(self, obj):
        """Exibe a quantidade de usuários nos setores secundários."""
        count = obj.get_usuarios_secundarios_count()
        return f"{count} usuário{'s' if count != 1 else ''}"
    exibir_usuarios_secundarios.short_description = 'Setores Secundários'


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioAdminForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'exibir_grupo_primario', 'telefone', 'ativo', 'data_criacao')
    list_filter = ('ativo', 'data_criacao', 'is_staff', 'is_active', 'grupo_primario', 'grupos_secundarios')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'grupo_primario__nome')
    list_editable = ('ativo',)
    readonly_fields = ('data_criacao', 'data_atualizacao', 'last_login', 'date_joined')
    ordering = ('username',)
    filter_horizontal = ('grupos_secundarios',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Setores e Permissões', {
            'fields': ('grupo_primario', 'grupos_secundarios')
        }),
        ('Informações Adicionais', {
            'fields': ('telefone', 'ativo', 'data_criacao', 'data_atualizacao')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Setores e Permissões', {
            'fields': ('grupo_primario', 'grupos_secundarios')
        }),
        ('Informações Adicionais', {
            'fields': ('email', 'first_name', 'last_name', 'telefone', 'ativo')
        }),
    )
    
    def exibir_grupo_primario(self, obj):
        """Exibe o setor principal do usuário."""
        if obj.grupo_primario:
            return obj.grupo_primario.get_hierarquia_completa()
        return '-'
    exibir_grupo_primario.short_description = 'Setor Principal'
    
    def get_queryset(self, request):
        """Otimiza consultas incluindo grupos."""
        return super().get_queryset(request).select_related('grupo_primario').prefetch_related('grupos_secundarios')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customiza o campo de setor principal para mostrar apenas grupos ativos."""
        if db_field.name == 'grupo_primario':
            kwargs['queryset'] = Grupo.objects.filter(ativo=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Customiza o campo de setores secundários para mostrar apenas grupos ativos."""
        if db_field.name == 'grupos_secundarios':
            kwargs['queryset'] = Grupo.objects.filter(ativo=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)