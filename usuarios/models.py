from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
import io


def validate_facial_image(image):
    """Valida se a imagem é adequada para reconhecimento facial."""
    if not image:
        return
    
    try:
        # Abre a imagem
        img = Image.open(image)
        
        # Verifica se é uma imagem
        img.verify()
        
        # Reabrir a imagem para mais validações (verify() consome o arquivo)
        image.seek(0)
        img = Image.open(image)
        
        # Validações de dimensões
        width, height = img.size
        if width < 100 or height < 100:
            raise ValidationError('A imagem deve ter pelo menos 100x100 pixels.')
        
        if width > 2000 or height > 2000:
            raise ValidationError('A imagem não pode ser maior que 2000x2000 pixels.')
        
        # Validação de formato
        if img.format not in ['JPEG', 'JPG', 'PNG']:
            raise ValidationError('Formato de imagem não suportado. Use JPEG ou PNG.')
        
        # Validação de tamanho do arquivo
        image.seek(0, 2)  # Vai para o final do arquivo
        file_size = image.tell()  # Obtém o tamanho
        image.seek(0)  # Volta ao início
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise ValidationError('A imagem deve ter no máximo 5MB.')
            
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError('Arquivo de imagem inválido.')


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
    permite_uso_reconhecimento_facial = models.BooleanField(
        default=False,
        verbose_name='Permite Reconhecimento Facial',
        help_text='Usuários deste grupo podem usar reconhecimento facial'
    )
    obriga_reconhecimento_facial = models.BooleanField(
        default=False,
        verbose_name='Obriga Reconhecimento Facial',
        help_text='Usuários deste grupo devem usar reconhecimento facial para autenticação'
    )
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
    
    # Campos para reconhecimento facial
    face_encoding = models.BinaryField(
        null=True,
        blank=True,
        verbose_name='Encoding Facial',
        help_text='Dados biométricos faciais criptografados'
    )
    foto_perfil_facial = models.ImageField(
        upload_to='faces/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Foto de Referência Facial',
        validators=[validate_facial_image],
        help_text='Upload de uma foto clara do rosto (JPG/PNG, máx. 5MB, mín. 100x100px)'
    )
    reconhecimento_facial_ativo = models.BooleanField(
        default=False,
        verbose_name='Reconhecimento Facial Ativo',
        help_text='Se o usuário tem reconhecimento facial cadastrado e ativo'
    )
    permite_reconhecimento_facial = models.BooleanField(
        default=False,
        verbose_name='Permite Reconhecimento Facial',
        help_text='Permissão administrativa para usar reconhecimento facial'
    )
    data_cadastro_facial = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Cadastro Facial'
    )
    tentativas_falhas_facial = models.IntegerField(
        default=0,
        verbose_name='Tentativas Falhas de Reconhecimento'
    )
    ultimo_acesso_facial = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Último Acesso via Reconhecimento Facial'
    )
    
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
    
    def pode_usar_reconhecimento_facial(self):
        """Verifica se o usuário pode usar reconhecimento facial."""
        if not self.permite_reconhecimento_facial:
            return False
        
        # Verifica permissão do grupo principal
        if self.grupo_primario and self.grupo_primario.permite_uso_reconhecimento_facial:
            return True
        
        # Verifica permissão nos grupos secundários
        return self.grupos_secundarios.filter(permite_uso_reconhecimento_facial=True).exists()
    
    def requer_reconhecimento_facial(self):
        """Verifica se o usuário é obrigado a usar reconhecimento facial."""
        if not self.reconhecimento_facial_ativo:
            return False
            
        # Verifica se o grupo principal obriga reconhecimento facial
        if self.grupo_primario and self.grupo_primario.obriga_reconhecimento_facial:
            return True
        
        # Verifica se algum grupo secundário obriga
        return self.grupos_secundarios.filter(obriga_reconhecimento_facial=True).exists()
    
    def resetar_tentativas_facial(self):
        """Reseta o contador de tentativas falhas."""
        self.tentativas_falhas_facial = 0
        self.save(update_fields=['tentativas_falhas_facial'])
    
    def incrementar_tentativas_facial(self):
        """Incrementa o contador de tentativas falhas."""
        self.tentativas_falhas_facial += 1
        self.save(update_fields=['tentativas_falhas_facial'])
        return self.tentativas_falhas_facial
    
    def otimizar_foto_facial(self):
        """Otimiza a foto facial redimensionando e comprimindo se necessário."""
        if not self.foto_perfil_facial:
            return False
            
        try:
            # Abre a imagem
            image = Image.open(self.foto_perfil_facial)
            
            # Converte para RGB se necessário
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Redimensiona se muito grande, mantendo a proporção
            max_size = 800
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Salva a imagem otimizada
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            # Atualiza o campo com a imagem otimizada
            self.foto_perfil_facial.save(
                self.foto_perfil_facial.name,
                InMemoryUploadedFile(
                    output, 'ImageField', self.foto_perfil_facial.name,
                    'image/jpeg', len(output.getvalue()), None
                ),
                save=False
            )
            
            return True
            
        except Exception as e:
            print(f"Erro ao otimizar foto facial: {e}")
            return False


class RegistroAcessoFacial(models.Model):
    """Modelo para registrar todos os acessos via reconhecimento facial."""
    
    TIPO_ACESSO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('tentativa_falha', 'Tentativa Falha'),
        ('cadastro', 'Cadastro Facial'),
        ('atualizacao', 'Atualização Facial'),
    ]
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='registros_faciais',
        verbose_name='Usuário',
        null=True,
        blank=True,
        help_text='Usuário identificado (null se falha na identificação)'
    )
    data_hora = models.DateTimeField(
        default=timezone.now,
        verbose_name='Data e Hora'
    )
    tipo_acesso = models.CharField(
        max_length=20,
        choices=TIPO_ACESSO_CHOICES,
        verbose_name='Tipo de Acesso'
    )
    confianca = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Confiança (%)',
        help_text='Percentual de confiança no reconhecimento'
    )
    foto_capturada = models.ImageField(
        upload_to='acessos/%Y/%m/%d/',
        verbose_name='Foto Capturada'
    )
    ip_origem = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP de Origem'
    )
    sucesso = models.BooleanField(
        default=False,
        verbose_name='Sucesso'
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações',
        help_text='Detalhes adicionais do acesso'
    )
    dispositivo = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Dispositivo',
        help_text='Informações do dispositivo usado'
    )
    
    class Meta:
        verbose_name = 'Registro de Acesso Facial'
        verbose_name_plural = 'Registros de Acesso Facial'
        ordering = ['-data_hora']
        indexes = [
            models.Index(fields=['-data_hora']),
            models.Index(fields=['usuario', '-data_hora']),
            models.Index(fields=['tipo_acesso', 'sucesso']),
        ]
    
    def __str__(self):
        if self.usuario:
            return f"{self.usuario} - {self.get_tipo_acesso_display()} - {self.data_hora}"
        return f"Acesso não identificado - {self.data_hora}"
    
    def save(self, *args, **kwargs):
        """Override para atualizar o último acesso do usuário se for sucesso."""
        super().save(*args, **kwargs)
        
        if self.usuario and self.sucesso and self.tipo_acesso in ['entrada', 'saida']:
            self.usuario.ultimo_acesso_facial = self.data_hora
            self.usuario.save(update_fields=['ultimo_acesso_facial'])