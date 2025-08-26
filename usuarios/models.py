from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser


class Grupo(models.Model):
    nome = models.CharField(max_length=100, verbose_name='Nome')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    grupo_pai = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subgrupos',
        verbose_name='Grupo Pai'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Última Atualização')

    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'
        ordering = ['nome']

    def __str__(self):
        if self.grupo_pai:
            return f"{self.grupo_pai} > {self.nome}"
        return self.nome

    def get_hierarquia_completa(self):
        """Retorna o caminho completo da hierarquia do grupo."""
        hierarquia = []
        grupo_atual = self
        while grupo_atual:
            hierarquia.insert(0, grupo_atual.nome)
            grupo_atual = grupo_atual.grupo_pai
        return ' > '.join(hierarquia)

    def clean(self):
        """Valida para evitar referências circulares na hierarquia."""
        if self.grupo_pai:
            if self.grupo_pai == self:
                raise ValidationError('Um grupo não pode ser pai de si mesmo.')
            
            grupos_pais = set()
            grupo_atual = self.grupo_pai
            while grupo_atual:
                if grupo_atual in grupos_pais:
                    raise ValidationError('Referência circular detectada na hierarquia de grupos.')
                if self.pk and grupo_atual.pk == self.pk:
                    raise ValidationError('Referência circular detectada: este grupo está na sua própria hierarquia pai.')
                grupos_pais.add(grupo_atual)
                grupo_atual = grupo_atual.grupo_pai

    def get_todos_subgrupos(self):
        """Retorna todos os subgrupos recursivamente."""
        subgrupos = list(self.subgrupos.all())
        for subgrupo in self.subgrupos.all():
            subgrupos.extend(subgrupo.get_todos_subgrupos())
        return subgrupos

    def get_nivel_hierarquia(self):
        """Retorna o nível na hierarquia (0 para grupos raiz)."""
        nivel = 0
        grupo_atual = self.grupo_pai
        while grupo_atual:
            nivel += 1
            grupo_atual = grupo_atual.grupo_pai
        return nivel
    
    def get_usuarios_primarios_count(self):
        """Retorna a quantidade de usuários que têm este grupo como primário."""
        return self.usuarios_primarios.count()
    
    def get_usuarios_secundarios_count(self):
        """Retorna a quantidade de usuários que têm este grupo como secundário."""
        return self.usuarios_secundarios.count()
    
    def get_total_usuarios(self):
        """Retorna o total de usuários associados a este grupo."""
        return self.get_usuarios_primarios_count() + self.get_usuarios_secundarios_count()


class Usuario(AbstractUser):
    grupo_primario = models.ForeignKey(
        'Grupo',
        on_delete=models.CASCADE,
        related_name='usuarios_primarios',
        verbose_name='Setor Principal',
        help_text='Setor principal do usuário (obrigatório)'
    )
    grupos_secundarios = models.ManyToManyField(
        'Grupo',
        blank=True,
        related_name='usuarios_secundarios',
        verbose_name='Setores Secundários',
        help_text='Setores adicionais do usuário (opcional)'
    )
    telefone = models.CharField(max_length=15, blank=True, verbose_name='Telefone')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Última Atualização')

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['username']

    def __str__(self):
        return self.get_full_name() or self.username
    
    def clean(self):
        """Validações customizadas do modelo."""
        super().clean()
        if not self.grupo_primario_id:
            raise ValidationError('Usuário deve ter um setor principal definido.')
        
        if self.grupo_primario and not self.grupo_primario.ativo:
            raise ValidationError('O setor principal deve estar ativo.')
        
        # Validação para evitar que o mesmo setor seja principal e secundário
        if self.grupo_primario and self.pk:
            # Verifica se o setor principal está nos setores secundários
            if self.grupos_secundarios.filter(id=self.grupo_primario.id).exists():
                raise ValidationError(
                    f'O setor "{self.grupo_primario.nome}" não pode ser tanto principal quanto secundário. '
                    'Remova-o dos setores secundários.'
                )
    
    def get_todos_grupos(self):
        """Retorna uma lista com o setor principal e todos os setores secundários."""
        grupos = [self.grupo_primario] if self.grupo_primario else []
        grupos.extend(list(self.grupos_secundarios.all()))
        return grupos
    
    def get_grupos_hierarquia(self):
        """Retorna os setores organizados por hierarquia."""
        todos_grupos = self.get_todos_grupos()
        return {
            'principal': self.grupo_primario,
            'secundarios': list(self.grupos_secundarios.all()),
            'todos': todos_grupos
        }
    
    def pertence_grupo(self, grupo):
        """Verifica se o usuário pertence a um setor específico."""
        if self.grupo_primario == grupo:
            return True
        return self.grupos_secundarios.filter(id=grupo.id).exists()
    
    def get_permissoes_grupos(self):
        """Método para futuras implementações de permissões por grupo."""
        # TODO: Implementar lógica de permissões
        return []
    
    def validar_setores_unicos(self, raise_exception=True):
        """Valida se não há duplicação entre setor principal e secundários."""
        if not self.grupo_primario or not self.pk:
            return True
        
        # Verifica se há duplicação
        tem_duplicacao = self.grupos_secundarios.filter(id=self.grupo_primario.id).exists()
        
        if tem_duplicacao:
            if raise_exception:
                raise ValidationError(
                    [f'O setor "{self.grupo_primario.nome}" não pode ser tanto principal quanto secundário.']
                )
            return False
        
        return True
    
    def save(self, *args, **kwargs):
        """Override do save para validar setores únicos."""
        # Valida antes de salvar (para casos sem m2m ainda)
        if self.pk and hasattr(self, '_state') and not self._state.adding:
            self.clean()
        
        # Salva primeiro para que o objeto tenha um ID
        super().save(*args, **kwargs)
        
        # Depois valida e corrige os setores para evitar duplicação
        self._corrigir_setores_duplicados()
    
    def _corrigir_setores_duplicados(self):
        """Corrige automaticamente setores duplicados removendo do secundário."""
        if not self.grupo_primario or not self.pk:
            return
        
        # Verifica e remove o setor principal dos secundários se existir
        if self.grupos_secundarios.filter(id=self.grupo_primario.id).exists():
            self.grupos_secundarios.remove(self.grupo_primario)
            print(f'Auto-correcção: Setor "{self.grupo_primario.nome}" removido dos secundários pois já é principal.')