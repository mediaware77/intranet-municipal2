/**
 * JavaScript para Reconhecimento Facial
 * Sistema de Intranet Municipal
 */

class FacialRecognition {
    constructor() {
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.stream = null;
        this.isCapturing = false;
        this.isProcessing = false;
        
        // Configurações
        this.config = {
            video: {
                width: 640,
                height: 480,
                facingMode: 'user'
            },
            capture: {
                quality: 0.8,
                format: 'image/jpeg'
            },
            detection: {
                interval: 100, // ms entre tentativas de detecção
                confidenceThreshold: 0.6
            }
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.checkBrowserSupport();
    }
    
    setupEventListeners() {
        document.addEventListener('DOMContentLoaded', () => {
            this.video = document.getElementById('video');
            this.canvas = document.getElementById('canvas');
            
            if (this.canvas) {
                this.context = this.canvas.getContext('2d');
            }
        });
    }
    
    checkBrowserSupport() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.showError('Seu navegador não suporta acesso à câmera. Atualize para uma versão mais recente.');
            return false;
        }
        return true;
    }
    
    async startCamera() {
        if (!this.checkBrowserSupport()) {
            return false;
        }
        
        try {
            this.showLoading('Iniciando câmera...');
            
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: this.config.video,
                audio: false
            });
            
            if (this.video) {
                this.video.srcObject = this.stream;
                this.video.play();
                
                // Aguarda o vídeo estar pronto
                return new Promise((resolve) => {
                    this.video.onloadedmetadata = () => {
                        this.hideLoading();
                        this.showSuccess('Câmera iniciada com sucesso!');
                        resolve(true);
                    };
                });
            }
            
        } catch (error) {
            console.error('Erro ao acessar câmera:', error);
            this.hideLoading();
            
            if (error.name === 'NotAllowedError') {
                this.showError('Acesso à câmera negado. Clique no ícone da câmera na barra de endereços e permita o acesso.');
            } else if (error.name === 'NotFoundError') {
                this.showError('Nenhuma câmera encontrada no dispositivo.');
            } else {
                this.showError('Erro ao acessar a câmera: ' + error.message);
            }
            
            return false;
        }
    }
    
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                track.stop();
            });
            this.stream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
        
        this.isCapturing = false;
        this.isProcessing = false;
    }
    
    captureFrame() {
        if (!this.video || !this.canvas || !this.context) {
            this.showError('Elementos de vídeo não encontrados.');
            return null;
        }
        
        if (this.video.readyState !== 4) {
            this.showWarning('Câmera ainda não está pronta. Aguarde...');
            return null;
        }
        
        // Define dimensões do canvas igual ao vídeo
        this.canvas.width = this.video.videoWidth || this.config.video.width;
        this.canvas.height = this.video.videoHeight || this.config.video.height;
        
        // Desenha o frame atual do vídeo no canvas
        this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        // Converte para base64
        const imageData = this.canvas.toDataURL(
            this.config.capture.format, 
            this.config.capture.quality
        );
        
        return imageData;
    }
    
    async processImage(imageData, endpoint, additionalData = {}) {
        if (this.isProcessing) {
            this.showWarning('Processamento em andamento, aguarde...');
            return null;
        }
        
        this.isProcessing = true;
        this.showLoading('Processando imagem...');
        
        try {
            const payload = {
                image: imageData,
                ...additionalData
            };
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.hideLoading();
            
            if (result.success) {
                this.showSuccess(result.message);
            } else {
                this.showError(result.message);
            }
            
            return result;
            
        } catch (error) {
            console.error('Erro ao processar imagem:', error);
            this.hideLoading();
            this.showError('Erro de conexão. Verifique sua internet e tente novamente.');
            return null;
            
        } finally {
            this.isProcessing = false;
        }
    }
    
    // Métodos específicos para cadastro facial
    async cadastrarFace() {
        const imageData = this.captureFrame();
        if (!imageData) return;
        
        const result = await this.processImage(imageData, window.location.pathname);
        
        if (result && result.success) {
            setTimeout(() => {
                window.location.href = '/usuarios/';
            }, 2000);
        }
        
        return result;
    }
    
    // Métodos específicos para login facial
    async loginFacial(username = '') {
        const imageData = this.captureFrame();
        if (!imageData) return;
        
        const result = await this.processImage(imageData, '/usuarios/facial/login/', {
            username: username
        });
        
        if (result && result.success && result.redirect_url) {
            setTimeout(() => {
                window.location.href = result.redirect_url;
            }, 1500);
        }
        
        return result;
    }
    
    // Detecção automática de faces (para preview)
    startFaceDetection() {
        if (!this.video || this.isCapturing) return;
        
        this.isCapturing = true;
        const detection = setInterval(() => {
            if (!this.isCapturing || !this.video) {
                clearInterval(detection);
                return;
            }
            
            // Aqui você pode implementar detecção de faces em tempo real
            // usando bibliotecas como face-api.js se necessário
            this.updateFacePreview();
            
        }, this.config.detection.interval);
    }
    
    stopFaceDetection() {
        this.isCapturing = false;
    }
    
    updateFacePreview() {
        // Implementar preview de detecção facial se necessário
        // Por enquanto, apenas verifica se o vídeo está ativo
        if (this.video && this.video.readyState === 4) {
            const previewElement = document.querySelector('.face-detection-overlay');
            if (previewElement) {
                previewElement.style.borderColor = '#28a745'; // Verde quando detecta vídeo
            }
        }
    }
    
    // Utilitários para UI
    showMessage(message, type = 'info') {
        const messageArea = document.getElementById('messageArea');
        if (!messageArea) return;
        
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';
        
        const icon = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation-circle',
            'info': 'fa-info-circle'
        }[type] || 'fa-info-circle';
        
        messageArea.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas ${icon}"></i> ${message}
                <button type="button" class="close" data-dismiss="alert">
                    <span>&times;</span>
                </button>
            </div>
        `;
        
        // Auto-hide após 5 segundos para mensagens de sucesso
        if (type === 'success') {
            setTimeout(() => {
                const alert = messageArea.querySelector('.alert');
                if (alert) {
                    alert.classList.remove('show');
                    setTimeout(() => alert.remove(), 150);
                }
            }, 5000);
        }
    }
    
    showSuccess(message) { this.showMessage(message, 'success'); }
    showError(message) { this.showMessage(message, 'error'); }
    showWarning(message) { this.showMessage(message, 'warning'); }
    showInfo(message) { this.showMessage(message, 'info'); }
    
    showLoading(message = 'Processando...') {
        const loadingElement = document.getElementById('loadingIndicator');
        if (loadingElement) {
            loadingElement.classList.remove('d-none');
            const messageEl = loadingElement.querySelector('p');
            if (messageEl) messageEl.textContent = message;
        }
    }
    
    hideLoading() {
        const loadingElement = document.getElementById('loadingIndicator');
        if (loadingElement) {
            loadingElement.classList.add('d-none');
        }
    }
    
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }
    
    // Validações de segurança
    validateImageQuality(imageData) {
        // Implementar validações básicas de qualidade da imagem
        if (!imageData || imageData.length < 1000) {
            this.showWarning('Imagem muito pequena ou corrompida');
            return false;
        }
        return true;
    }
    
    // Cleanup quando sair da página
    cleanup() {
        this.stopCamera();
        this.stopFaceDetection();
    }
}

// Instância global
window.facialRecognition = new FacialRecognition();

// Cleanup automático quando sair da página
window.addEventListener('beforeunload', () => {
    if (window.facialRecognition) {
        window.facialRecognition.cleanup();
    }
});

// Exportar para uso em outros scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FacialRecognition;
}