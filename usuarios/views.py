from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import update_session_auth_hash, login
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.exceptions import ValidationError
import base64
import json
from .forms import PerfilUsuarioForm, AlterarSenhaForm
from .models import Usuario, RegistroAcessoFacial

# Importações condicionais para reconhecimento facial
try:
    import cv2
    import numpy as np
    from .facial_security import FacialSecurityManager
    FACIAL_RECOGNITION_AVAILABLE = True
except ImportError:
    FACIAL_RECOGNITION_AVAILABLE = False


class CustomLoginView(LoginView):
    template_name = 'usuarios/login.html'
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    context = {
        'usuario': request.user,
    }
    return render(request, 'usuarios/dashboard.html', context)


@login_required
def perfil(request):
    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('perfil')
    else:
        form = PerfilUsuarioForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'usuarios/perfil.html', context)


@login_required
def alterar_senha(request):
    if request.method == 'POST':
        form = AlterarSenhaForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('dashboard')
    else:
        form = AlterarSenhaForm(user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'usuarios/alterar_senha.html', context)


def get_client_ip(request):
    """Obtém o IP do cliente."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def decode_base64_image(image_data):
    """Converte imagem base64 para array OpenCV."""
    if not FACIAL_RECOGNITION_AVAILABLE:
        return None
        
    try:
        # Remove o prefixo data:image/...;base64,
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decodifica base64
        image_bytes = base64.b64decode(image_data)
        
        # Converte para numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        
        # Decodifica como imagem
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return image
    except Exception as e:
        return None


@login_required
def cadastrar_face(request):
    """View para cadastro de reconhecimento facial."""
    # Verifica se a funcionalidade está disponível
    if not FACIAL_RECOGNITION_AVAILABLE:
        messages.error(request, 'Funcionalidade de reconhecimento facial não está disponível. Instale as dependências necessárias.')
        return redirect('dashboard')
    
    # Verifica se o usuário tem permissão
    if not request.user.permite_reconhecimento_facial:
        messages.error(request, 'Você não tem permissão para usar reconhecimento facial.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image')
            
            if not image_data:
                return JsonResponse({'success': False, 'message': 'Imagem não fornecida'})
            
            # Converte base64 para imagem
            image = decode_base64_image(image_data)
            if image is None:
                return JsonResponse({'success': False, 'message': 'Erro ao processar imagem'})
            
            # Processa o cadastro facial
            facial_manager = FacialSecurityManager()
            success, message = facial_manager.register_face(request.user, image)
            
            if success:
                # Salva a foto de perfil facial
                if FACIAL_RECOGNITION_AVAILABLE:
                    _, buffer = cv2.imencode('.jpg', image)
                    image_file = ContentFile(buffer.tobytes())
                    filename = f'perfil_facial_{request.user.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.jpg'
                    request.user.foto_perfil_facial.save(filename, image_file)
                    
                    # Registra o evento
                    _, buffer = cv2.imencode('.jpg', image)
                    foto_file = ContentFile(buffer.tobytes())
                
                registro = RegistroAcessoFacial.objects.create(
                    usuario=request.user,
                    tipo_acesso='cadastro',
                    ip_origem=get_client_ip(request),
                    sucesso=True,
                    observacoes='Cadastro facial realizado com sucesso',
                    dispositivo=request.META.get('HTTP_USER_AGENT', '')[:200]
                )
                if FACIAL_RECOGNITION_AVAILABLE:
                    registro.foto_capturada.save(
                        f'cadastro_{request.user.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.jpg',
                        foto_file
                    )
                
                messages.success(request, 'Face cadastrada com sucesso!')
            
            return JsonResponse({'success': success, 'message': message})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})
    
    context = {
        'usuario': request.user,
        'tem_face_cadastrada': request.user.reconhecimento_facial_ativo,
        'pode_usar_facial': request.user.pode_usar_reconhecimento_facial()
    }
    return render(request, 'usuarios/cadastro_facial.html', context)


@csrf_exempt
@require_POST
def login_facial(request):
    """View para autenticação via reconhecimento facial."""
    if not FACIAL_RECOGNITION_AVAILABLE:
        return JsonResponse({'success': False, 'message': 'Funcionalidade de reconhecimento facial não disponível'})
    
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        username = data.get('username', '')  # Opcional: username para busca direcionada
        
        if not image_data:
            return JsonResponse({'success': False, 'message': 'Imagem não fornecida'})
        
        # Converte base64 para imagem
        image = decode_base64_image(image_data)
        if image is None:
            return JsonResponse({'success': False, 'message': 'Erro ao processar imagem'})
        
        # Processa o login facial
        facial_manager = FacialSecurityManager()
        
        # Se username foi fornecido, busca usuário específico
        target_user = None
        if username:
            try:
                target_user = Usuario.objects.get(username=username, ativo=True)
                if not target_user.pode_usar_reconhecimento_facial():
                    return JsonResponse({
                        'success': False, 
                        'message': 'Usuário não tem permissão para reconhecimento facial'
                    })
            except Usuario.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Usuário não encontrado'})
        
        result = facial_manager.process_facial_login(image, target_user)
        
        # Registra a tentativa de acesso
        registro = RegistroAcessoFacial.objects.create(
            usuario=result.get('user'),
            tipo_acesso='entrada' if result['success'] else 'tentativa_falha',
            confianca=result.get('confidence', 0),
            ip_origem=get_client_ip(request),
            sucesso=result['success'],
            observacoes=result['message'],
            dispositivo=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        if FACIAL_RECOGNITION_AVAILABLE:
            _, buffer = cv2.imencode('.jpg', image)
            foto_file = ContentFile(buffer.tobytes())
            registro.foto_capturada.save(
                f'login_{timezone.now().strftime("%Y%m%d_%H%M%S")}.jpg',
                foto_file
            )
        
        # Se login bem-sucedido, autentica o usuário
        if result['success'] and result['user']:
            login(request, result['user'])
            result['redirect_url'] = '/usuarios/dashboard/'
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})


@login_required
def historico_facial(request):
    """View para exibir histórico de acessos faciais."""
    if not request.user.pode_usar_reconhecimento_facial():
        return HttpResponseForbidden('Acesso negado')
    
    registros = RegistroAcessoFacial.objects.filter(
        usuario=request.user
    ).order_by('-data_hora')[:50]  # Últimos 50 registros
    
    context = {
        'registros': registros,
        'usuario': request.user
    }
    return render(request, 'usuarios/historico_facial.html', context)


@login_required
@require_POST
def remover_facial(request):
    """View para remover cadastro facial."""
    if not request.user.reconhecimento_facial_ativo:
        return JsonResponse({'success': False, 'message': 'Não há cadastro facial ativo'})
    
    try:
        # Remove dados faciais
        request.user.face_encoding = None
        request.user.reconhecimento_facial_ativo = False
        request.user.data_cadastro_facial = None
        request.user.tentativas_falhas_facial = 0
        
        # Remove foto de perfil facial se existir
        if request.user.foto_perfil_facial:
            request.user.foto_perfil_facial.delete()
        
        request.user.save()
        
        # Registra a remoção
        RegistroAcessoFacial.objects.create(
            usuario=request.user,
            tipo_acesso='atualizacao',
            ip_origem=get_client_ip(request),
            sucesso=True,
            observacoes='Cadastro facial removido pelo usuário',
            dispositivo=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        messages.success(request, 'Cadastro facial removido com sucesso!')
        return JsonResponse({'success': True, 'message': 'Cadastro facial removido'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao remover cadastro: {str(e)}'})


@login_required
def facial_login_page(request):
    """Página de login facial."""
    if request.user.is_authenticated and not request.GET.get('force'):
        return redirect('dashboard')
    
    # Se usuário está logado mas precisa de verificação facial adicional
    context = {
        'require_facial': request.GET.get('require_facial', False),
        'username': request.GET.get('username', ''),
    }
    return render(request, 'usuarios/login_facial.html', context)


@permission_required('usuarios.view_registroacessofacial', raise_exception=True)
def admin_historico_facial(request):
    """View para administradores visualizarem todos os logs faciais."""
    registros = RegistroAcessoFacial.objects.all().order_by('-data_hora')[:100]
    
    context = {
        'registros': registros,
        'is_admin_view': True
    }
    return render(request, 'usuarios/admin_historico_facial.html', context)


@login_required
def atualizar_foto_facial(request):
    """View para atualizar foto facial via upload."""
    
    # Verifica se o usuário pode usar reconhecimento facial
    pode_usar = request.user.pode_usar_reconhecimento_facial()
    
    if request.method == 'POST':
        if not pode_usar:
            messages.error(request, 'Você não tem permissão para usar reconhecimento facial.')
            return redirect('dashboard')
            
        foto = request.FILES.get('foto_perfil_facial')
        if not foto:
            messages.error(request, 'Nenhuma foto foi selecionada.')
            return redirect('atualizar_foto_facial')
        
        try:
            # Salva a foto antiga para possível rollback
            foto_antiga = request.user.foto_perfil_facial.name if request.user.foto_perfil_facial else None
            
            # Atualiza a foto
            request.user.foto_perfil_facial = foto
            request.user.full_clean()  # Valida o modelo
            
            # Otimiza a foto
            if request.user.otimizar_foto_facial():
                print("Foto otimizada com sucesso")
            
            # Processa para reconhecimento facial se disponível
            if FACIAL_RECOGNITION_AVAILABLE:
                try:
                    manager = FacialSecurityManager()
                    success = manager.processar_nova_foto_usuario(request.user)
                    
                    if success:
                        request.user.data_cadastro_facial = timezone.now()
                        request.user.reconhecimento_facial_ativo = True
                        request.user.tentativas_falhas_facial = 0
                        
                        # Registra a atualização
                        RegistroAcessoFacial.objects.create(
                            usuario=request.user,
                            tipo_acesso='atualizacao',
                            ip_origem=get_client_ip(request),
                            sucesso=True,
                            observacoes='Foto facial atualizada via upload',
                            dispositivo=request.META.get('HTTP_USER_AGENT', '')[:200]
                        )
                        
                        messages.success(request, 'Foto facial atualizada e processada com sucesso!')
                    else:
                        messages.warning(request, 'Foto salva, mas não foi possível detectar um rosto. Tente novamente com uma foto mais clara.')
                        
                except Exception as e:
                    messages.warning(request, f'Foto salva, mas ocorreu um erro no processamento: {str(e)}')
            else:
                messages.success(request, 'Foto salva com sucesso! (Processamento facial não disponível)')
            
            request.user.save()
            return redirect('dashboard')
            
        except ValidationError as e:
            messages.error(request, f'Erro na validação da imagem: {"; ".join(e.messages)}')
        except Exception as e:
            messages.error(request, f'Erro ao salvar a foto: {str(e)}')
            
        return redirect('atualizar_foto_facial')
    
    context = {
        'pode_usar_facial': pode_usar,
        'usuario': request.user
    }
    return render(request, 'usuarios/atualizar_foto_facial.html', context)


@login_required
@require_POST
def remover_foto_facial(request):
    """View para remover apenas a foto facial (mantém outros dados)."""
    
    if not request.user.foto_perfil_facial:
        messages.warning(request, 'Não há foto cadastrada para remover.')
        return redirect('dashboard')
    
    try:
        # Remove a foto
        request.user.foto_perfil_facial.delete()
        
        # Desativa reconhecimento facial mas mantém permissões
        request.user.reconhecimento_facial_ativo = False
        request.user.face_encoding = None
        request.user.data_cadastro_facial = None
        request.user.tentativas_falhas_facial = 0
        
        request.user.save()
        
        # Registra a remoção
        RegistroAcessoFacial.objects.create(
            usuario=request.user,
            tipo_acesso='atualizacao',
            ip_origem=get_client_ip(request),
            sucesso=True,
            observacoes='Foto facial removida pelo usuário',
            dispositivo=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        messages.success(request, 'Foto facial removida com sucesso!')
        
    except Exception as e:
        messages.error(request, f'Erro ao remover foto: {str(e)}')
    
    return redirect('atualizar_foto_facial')