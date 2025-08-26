import base64
import pickle
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

# Importações condicionais
try:
    import numpy as np
    import cv2
    import face_recognition
    FACIAL_LIBS_AVAILABLE = True
except ImportError:
    FACIAL_LIBS_AVAILABLE = False

logger = logging.getLogger(__name__)


class FacialSecurityManager:
    """Gerenciador de segurança para reconhecimento facial."""
    
    def __init__(self):
        if not FACIAL_LIBS_AVAILABLE:
            logger.warning("Bibliotecas de reconhecimento facial não disponíveis")
        
        self.confidence_threshold = getattr(settings, 'FACIAL_CONFIDENCE_THRESHOLD', 0.6)
        self.max_attempts = getattr(settings, 'FACIAL_MAX_ATTEMPTS', 3)
        self.attempt_timeout = getattr(settings, 'FACIAL_ATTEMPT_TIMEOUT', 300)
        self._cipher = None
    
    @property
    def cipher(self):
        """Obtém ou cria a chave de criptografia."""
        if not self._cipher:
            # Em produção, esta chave deve ser armazenada de forma segura
            key = getattr(settings, 'FACIAL_ENCRYPTION_KEY', None)
            if not key:
                # Gera uma chave baseada no SECRET_KEY do Django
                key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32))[:44]
            else:
                key = key.encode() if isinstance(key, str) else key
            self._cipher = Fernet(key)
        return self._cipher
    
    def encrypt_encoding(self, face_encoding):
        """Criptografa o encoding facial para armazenamento."""
        if face_encoding is None:
            return None
        
        try:
            # Serializa o numpy array
            encoded_data = pickle.dumps(face_encoding)
            # Criptografa
            encrypted = self.cipher.encrypt(encoded_data)
            return encrypted
        except Exception as e:
            logger.error(f"Erro ao criptografar encoding: {e}")
            return None
    
    def decrypt_encoding(self, encrypted_encoding):
        """Descriptografa o encoding facial."""
        if encrypted_encoding is None:
            return None
        
        try:
            # Descriptografa
            decrypted = self.cipher.decrypt(bytes(encrypted_encoding))
            # Deserializa
            face_encoding = pickle.loads(decrypted)
            return face_encoding
        except Exception as e:
            logger.error(f"Erro ao descriptografar encoding: {e}")
            return None
    
    def extract_face_encoding(self, image):
        """Extrai o encoding facial de uma imagem."""
        if not FACIAL_LIBS_AVAILABLE:
            return None, "Bibliotecas de reconhecimento facial não disponíveis"
            
        try:
            # Converte para RGB se necessário
            if len(image.shape) == 2:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            else:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detecta faces na imagem
            face_locations = face_recognition.face_locations(rgb_image)
            
            if not face_locations:
                return None, "Nenhuma face detectada na imagem"
            
            if len(face_locations) > 1:
                return None, "Múltiplas faces detectadas. Por favor, certifique-se de que apenas uma pessoa está na imagem"
            
            # Extrai o encoding da face detectada
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            if face_encodings:
                return face_encodings[0], None
            
            return None, "Não foi possível extrair características faciais"
            
        except Exception as e:
            logger.error(f"Erro ao extrair face encoding: {e}")
            return None, str(e)
    
    def compare_faces(self, known_encoding, unknown_encoding, tolerance=None):
        """Compara dois encodings faciais."""
        if not FACIAL_LIBS_AVAILABLE:
            return False, 0
            
        if tolerance is None:
            tolerance = 1 - self.confidence_threshold
        
        try:
            # Calcula a distância entre os encodings
            distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
            
            # Converte distância em confiança percentual
            confidence = (1 - distance) * 100
            
            # Verifica se é um match
            is_match = distance <= tolerance
            
            return is_match, confidence
            
        except Exception as e:
            logger.error(f"Erro ao comparar faces: {e}")
            return False, 0
    
    def validate_liveness(self, image):
        """Validação básica anti-spoofing (detecção de foto vs pessoa real)."""
        if not FACIAL_LIBS_AVAILABLE:
            return True, "Validação de liveness não disponível"
            
        try:
            # Converte para escala de cinza
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calcula o Laplaciano (detecta blur/foco)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Se a imagem está muito desfocada, pode ser uma foto de foto
            if laplacian_var < 100:
                return False, "Imagem muito desfocada. Por favor, ajuste o foco da câmera"
            
            # Análise de histograma para detectar impressões
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist_normalized = hist.ravel() / hist.sum()
            
            # Calcula entropia (imagens impressas tendem a ter menor entropia)
            entropy = -sum([p * np.log2(p + 1e-7) for p in hist_normalized if p > 0])
            
            if entropy < 4.5:
                return False, "Possível tentativa de spoofing detectada"
            
            return True, "Validação de liveness aprovada"
            
        except Exception as e:
            logger.error(f"Erro na validação de liveness: {e}")
            return True, "Validação de liveness não disponível"
    
    def check_attempt_limit(self, user_id):
        """Verifica se o usuário excedeu o limite de tentativas."""
        cache_key = f"facial_attempts_{user_id}"
        attempts = cache.get(cache_key, 0)
        
        if attempts >= self.max_attempts:
            return False, f"Limite de {self.max_attempts} tentativas excedido. Tente novamente em alguns minutos"
        
        return True, attempts
    
    def increment_attempts(self, user_id):
        """Incrementa o contador de tentativas falhas."""
        cache_key = f"facial_attempts_{user_id}"
        attempts = cache.get(cache_key, 0)
        cache.set(cache_key, attempts + 1, self.attempt_timeout)
        return attempts + 1
    
    def reset_attempts(self, user_id):
        """Reseta o contador de tentativas."""
        cache_key = f"facial_attempts_{user_id}"
        cache.delete(cache_key)
    
    def process_facial_login(self, image, user=None):
        """Processa tentativa de login facial."""
        from .models import Usuario, RegistroAcessoFacial
        
        # Valida liveness
        is_live, liveness_msg = self.validate_liveness(image)
        if not is_live:
            return {
                'success': False,
                'message': liveness_msg,
                'user': None
            }
        
        # Extrai encoding da imagem
        face_encoding, error_msg = self.extract_face_encoding(image)
        if face_encoding is None:
            return {
                'success': False,
                'message': error_msg or "Não foi possível processar a face",
                'user': None
            }
        
        # Se um usuário específico foi fornecido, verifica apenas ele
        if user:
            if not user.reconhecimento_facial_ativo or not user.face_encoding:
                return {
                    'success': False,
                    'message': "Reconhecimento facial não configurado para este usuário",
                    'user': None
                }
            
            # Descriptografa o encoding armazenado
            stored_encoding = self.decrypt_encoding(user.face_encoding)
            if stored_encoding is None:
                return {
                    'success': False,
                    'message': "Erro ao acessar dados faciais do usuário",
                    'user': None
                }
            
            # Compara faces
            is_match, confidence = self.compare_faces(stored_encoding, face_encoding)
            
            if is_match:
                user.resetar_tentativas_facial()
                self.reset_attempts(user.id)
                return {
                    'success': True,
                    'message': f"Reconhecimento bem-sucedido (confiança: {confidence:.1f}%)",
                    'user': user,
                    'confidence': confidence
                }
            else:
                user.incrementar_tentativas_facial()
                self.increment_attempts(user.id)
                return {
                    'success': False,
                    'message': f"Face não reconhecida (confiança: {confidence:.1f}%)",
                    'user': None,
                    'confidence': confidence
                }
        
        # Busca entre todos os usuários com reconhecimento facial ativo
        usuarios_com_facial = Usuario.objects.filter(
            reconhecimento_facial_ativo=True,
            face_encoding__isnull=False
        )
        
        melhor_match = None
        melhor_confianca = 0
        
        for usuario in usuarios_com_facial:
            stored_encoding = self.decrypt_encoding(usuario.face_encoding)
            if stored_encoding is None:
                continue
            
            is_match, confidence = self.compare_faces(stored_encoding, face_encoding)
            
            if is_match and confidence > melhor_confianca:
                melhor_match = usuario
                melhor_confianca = confidence
        
        if melhor_match:
            melhor_match.resetar_tentativas_facial()
            self.reset_attempts(melhor_match.id)
            return {
                'success': True,
                'message': f"Usuário identificado: {melhor_match.get_full_name()} (confiança: {melhor_confianca:.1f}%)",
                'user': melhor_match,
                'confidence': melhor_confianca
            }
        
        return {
            'success': False,
            'message': "Usuário não identificado",
            'user': None,
            'confidence': 0
        }
    
    def register_face(self, user, image):
        """Registra a face de um usuário."""
        # Valida liveness
        is_live, liveness_msg = self.validate_liveness(image)
        if not is_live:
            return False, liveness_msg
        
        # Extrai encoding
        face_encoding, error_msg = self.extract_face_encoding(image)
        if face_encoding is None:
            return False, error_msg or "Não foi possível processar a face"
        
        # Criptografa e salva
        encrypted = self.encrypt_encoding(face_encoding)
        if encrypted is None:
            return False, "Erro ao processar dados faciais"
        
        user.face_encoding = encrypted
        user.reconhecimento_facial_ativo = True
        user.data_cadastro_facial = timezone.now()
        user.save(update_fields=['face_encoding', 'reconhecimento_facial_ativo', 'data_cadastro_facial'])
        
        return True, "Face cadastrada com sucesso"
    
    def processar_nova_foto_usuario(self, usuario):
        """Processa nova foto de perfil facial de um usuário."""
        if not usuario.foto_perfil_facial:
            return False
            
        try:
            # Abre a imagem da foto de perfil
            from PIL import Image as PILImage
            import io
            
            # Abre a imagem do campo ImageField
            with usuario.foto_perfil_facial.open('rb') as foto_file:
                pil_image = PILImage.open(foto_file)
                
                # Converte PIL para array numpy/OpenCV
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                
                import numpy as np
                cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                
                # Usa o método register_face existente
                success, message = self.register_face(usuario, cv_image)
                
                return success
                
        except Exception as e:
            logger.error(f"Erro ao processar foto do usuário {usuario.username}: {e}")
            return False