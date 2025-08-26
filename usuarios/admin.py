from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Usuario, Grupo, RegistroAcessoFacial

# Verificação de disponibilidade de reconhecimento facial
try:
    import cv2
    import numpy as np
    FACIAL_RECOGNITION_AVAILABLE = True
except ImportError:
    FACIAL_RECOGNITION_AVAILABLE = False


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
    list_display = ('exibir_hierarquia', 'nome', 'grupo_pai', 'ativo', 'permite_uso_reconhecimento_facial', 'obriga_reconhecimento_facial', 'exibir_usuarios_primarios', 'exibir_usuarios_secundarios', 'data_criacao')
    list_filter = ('ativo', 'permite_uso_reconhecimento_facial', 'obriga_reconhecimento_facial', 'data_criacao', 'grupo_pai')
    search_fields = ('nome', 'descricao', 'grupo_pai__nome')
    list_editable = ('ativo', 'permite_uso_reconhecimento_facial', 'obriga_reconhecimento_facial')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'exibir_hierarquia_completa', 'exibir_nivel')
    ordering = ('nome',)
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao', 'grupo_pai', 'ativo')
        }),
        ('Reconhecimento Facial', {
            'fields': ('permite_uso_reconhecimento_facial', 'obriga_reconhecimento_facial'),
            'description': 'Configurações de permissão para reconhecimento facial dos usuários deste grupo.'
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


class RegistroAcessoFacialInline(admin.TabularInline):
    model = RegistroAcessoFacial
    extra = 0
    readonly_fields = ('data_hora', 'tipo_acesso', 'confianca', 'ip_origem', 'sucesso', 'observacoes', 'dispositivo', 'exibir_foto_miniatura')
    fields = ('data_hora', 'tipo_acesso', 'confianca', 'sucesso', 'ip_origem', 'observacoes', 'exibir_foto_miniatura')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def exibir_foto_miniatura(self, obj):
        if obj.foto_capturada:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.foto_capturada.url
            )
        return "Sem foto"
    exibir_foto_miniatura.short_description = "Foto"


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioAdminForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'exibir_grupo_primario', 'telefone', 'ativo', 'exibir_status_facial', 'data_criacao')
    list_filter = ('ativo', 'reconhecimento_facial_ativo', 'permite_reconhecimento_facial', 'data_criacao', 'is_staff', 'is_active', 'grupo_primario', 'grupos_secundarios')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'grupo_primario__nome')
    list_editable = ('ativo',)
    readonly_fields = ('data_criacao', 'data_atualizacao', 'last_login', 'date_joined', 'exibir_foto_facial', 'data_cadastro_facial', 'ultimo_acesso_facial')
    ordering = ('username',)
    filter_horizontal = ('grupos_secundarios',)
    inlines = [RegistroAcessoFacialInline]
    
    actions = ['ativar_reconhecimento_facial', 'desativar_reconhecimento_facial', 'remover_dados_faciais', 'processar_fotos_pendentes']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Setores e Permissões', {
            'fields': ('grupo_primario', 'grupos_secundarios')
        }),
        ('Reconhecimento Facial', {
            'fields': ('permite_reconhecimento_facial', 'reconhecimento_facial_ativo', 'foto_perfil_facial', 'exibir_foto_facial', 'data_cadastro_facial', 'ultimo_acesso_facial', 'tentativas_falhas_facial'),
            'description': 'Configurações e status do reconhecimento facial do usuário. Faça upload de uma foto clara do rosto para ativar o reconhecimento facial.'
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
            'fields': ('email', 'first_name', 'last_name', 'telefone', 'ativo', 'permite_reconhecimento_facial')
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
    
    def exibir_status_facial(self, obj):
        """Exibe o status do reconhecimento facial."""
        if obj.reconhecimento_facial_ativo:
            return format_html('<span style="color: green;"><strong>✓ Ativo</strong></span>')
        elif obj.permite_reconhecimento_facial:
            return format_html('<span style="color: orange;">⚠ Permitido</span>')
        else:
            return format_html('<span style="color: red;">✗ Sem Permissão</span>')
    exibir_status_facial.short_description = 'Status Facial'
    
    def exibir_foto_facial(self, obj):
        """Exibe a foto facial do usuário no admin com melhor formatação."""
        if obj.foto_perfil_facial:
            return format_html(
                '<div style="text-align: center;">'
                '<img src="{}" width="120" height="120" style="object-fit: cover; border-radius: 8px; border: 2px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />'
                '<br><small style="color: #666; margin-top: 5px; display: inline-block;">Foto de referência</small>'
                '</div>',
                obj.foto_perfil_facial.url
            )
        return format_html(
            '<div style="text-align: center; padding: 20px; border: 2px dashed #ccc; border-radius: 8px; background: #f9f9f9;">'
            '<span style="color: #999; font-size: 24px;">📷</span><br>'
            '<small style="color: #666;">Nenhuma foto cadastrada</small>'
            '</div>'
        )
    exibir_foto_facial.short_description = "Foto de Referência Facial"
    
    def ativar_reconhecimento_facial(self, request, queryset):
        """Action para ativar permissão de reconhecimento facial."""
        updated = queryset.update(permite_reconhecimento_facial=True)
        self.message_user(request, f'{updated} usuário(s) teve(ram) o reconhecimento facial habilitado.')
    ativar_reconhecimento_facial.short_description = "Ativar permissão de reconhecimento facial"
    
    def desativar_reconhecimento_facial(self, request, queryset):
        """Action para desativar permissão de reconhecimento facial."""
        updated = queryset.update(permite_reconhecimento_facial=False, reconhecimento_facial_ativo=False)
        self.message_user(request, f'{updated} usuário(s) teve(ram) o reconhecimento facial desabilitado.')
    desativar_reconhecimento_facial.short_description = "Desativar reconhecimento facial"
    
    def remover_dados_faciais(self, request, queryset):
        """Action para remover todos os dados faciais dos usuários selecionados."""
        count = 0
        for usuario in queryset:
            if usuario.reconhecimento_facial_ativo:
                usuario.face_encoding = None
                usuario.reconhecimento_facial_ativo = False
                usuario.data_cadastro_facial = None
                usuario.tentativas_falhas_facial = 0
                if usuario.foto_perfil_facial:
                    usuario.foto_perfil_facial.delete()
                usuario.save()
                count += 1
        
        self.message_user(request, f'Dados faciais removidos para {count} usuário(s).')
    remover_dados_faciais.short_description = "Remover dados faciais"
    
    def processar_fotos_pendentes(self, request, queryset):
        """Action para processar fotos que foram enviadas mas não têm encoding."""
        if not FACIAL_RECOGNITION_AVAILABLE:
            self.message_user(request, 'Reconhecimento facial não está disponível.', level=messages.ERROR)
            return
            
        count_processados = 0
        count_falhas = 0
        
        for usuario in queryset:
            if usuario.foto_perfil_facial and not usuario.face_encoding:
                try:
                    from .facial_security import FacialSecurityManager
                    manager = FacialSecurityManager()
                    
                    # Processa a imagem para extrair encoding facial
                    success = manager.processar_nova_foto_usuario(usuario)
                    
                    if success:
                        count_processados += 1
                    else:
                        count_falhas += 1
                        
                except Exception as e:
                    count_falhas += 1
                    print(f"Erro ao processar foto do usuário {usuario.username}: {e}")
        
        if count_processados > 0:
            self.message_user(request, f'{count_processados} foto(s) processada(s) com sucesso.')
        if count_falhas > 0:
            self.message_user(request, f'{count_falhas} foto(s) falharam no processamento.', level=messages.WARNING)
            
    processar_fotos_pendentes.short_description = "Processar fotos pendentes para reconhecimento"


@admin.register(RegistroAcessoFacial)
class RegistroAcessoFacialAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'data_hora', 'tipo_acesso', 'confianca', 'sucesso', 'ip_origem', 'exibir_foto_miniatura')
    list_filter = ('tipo_acesso', 'sucesso', 'data_hora', 'usuario')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'ip_origem', 'observacoes')
    readonly_fields = ('usuario', 'data_hora', 'tipo_acesso', 'confianca', 'ip_origem', 'sucesso', 'observacoes', 'dispositivo', 'exibir_foto_completa')
    ordering = ('-data_hora',)
    
    fieldsets = (
        ('Informações do Acesso', {
            'fields': ('usuario', 'data_hora', 'tipo_acesso', 'sucesso', 'confianca')
        }),
        ('Detalhes Técnicos', {
            'fields': ('ip_origem', 'dispositivo', 'observacoes')
        }),
        ('Evidência Fotográfica', {
            'fields': ('exibir_foto_completa',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def exibir_foto_miniatura(self, obj):
        if obj.foto_capturada:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.foto_capturada.url
            )
        return "Sem foto"
    exibir_foto_miniatura.short_description = "Foto"
    
    def exibir_foto_completa(self, obj):
        if obj.foto_capturada:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; object-fit: contain; border-radius: 8px;" />',
                obj.foto_capturada.url
            )
        return "Sem foto capturada"
    exibir_foto_completa.short_description = "Foto Capturada"