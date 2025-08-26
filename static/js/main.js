// JavaScript para Intranet Municipal

document.addEventListener('DOMContentLoaded', function() {
    
    // Função para inicializar componentes
    initializeComponents();
    
    // Auto-hide alerts após 5 segundos
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            const alertInstance = new bootstrap.Alert(alert);
            alertInstance.close();
        });
    }, 5000);
    
    // Animação fade-in para cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(function(card, index) {
        card.classList.add('fade-in');
        card.style.animationDelay = (index * 0.1) + 's';
    });
    
    // Confirmação para ações críticas
    const criticalActions = document.querySelectorAll('[data-confirm]');
    criticalActions.forEach(function(action) {
        action.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Validação de formulários em tempo real
    initializeFormValidation();
    
    // Tooltip initialization
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Popover initialization
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

function initializeComponents() {
    // Sidebar toggle functionality
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    
    if (sidebarCollapse && sidebar && content) {
        sidebarCollapse.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            content.classList.toggle('active');
            
            // Salvar estado no localStorage
            const isCollapsed = sidebar.classList.contains('active');
            localStorage.setItem('sidebarCollapsed', isCollapsed);
        });
        
        // Restaurar estado do sidebar
        const savedState = localStorage.getItem('sidebarCollapsed');
        if (savedState === 'true') {
            sidebar.classList.add('active');
            content.classList.add('active');
        }
    }
    
    // Máscara para telefone
    const phoneInputs = document.querySelectorAll('input[name="telefone"]');
    phoneInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length <= 11) {
                value = value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
                if (value.length < 14) {
                    value = value.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
                }
            }
            e.target.value = value;
        });
    });
    
    // Feedback visual para loading states
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="loading me-2"></span>Processando...';
                submitBtn.disabled = true;
                
                // Restaurar botão após 10 segundos (fallback)
                setTimeout(function() {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 10000);
            }
        });
    });
}

function initializeFormValidation() {
    // Validação personalizada para campos de senha
    const passwordFields = document.querySelectorAll('input[type="password"]');
    passwordFields.forEach(function(field) {
        field.addEventListener('blur', validatePassword);
        field.addEventListener('input', function() {
            // Remove mensagens de erro enquanto o usuário digita
            clearFieldErrors(this);
        });
    });
    
    // Validação de email
    const emailFields = document.querySelectorAll('input[type="email"]');
    emailFields.forEach(function(field) {
        field.addEventListener('blur', validateEmail);
        field.addEventListener('input', function() {
            clearFieldErrors(this);
        });
    });
}

function validatePassword(e) {
    const field = e.target;
    const value = field.value;
    
    if (field.name === 'new_password1' && value) {
        const requirements = [
            { test: value.length >= 8, message: 'Deve ter pelo menos 8 caracteres' },
            { test: /[A-Z]/.test(value), message: 'Deve conter pelo menos uma letra maiúscula' },
            { test: /[a-z]/.test(value), message: 'Deve conter pelo menos uma letra minúscula' },
            { test: /\d/.test(value), message: 'Deve conter pelo menos um número' }
        ];
        
        showPasswordStrength(field, requirements);
    }
}

function validateEmail(e) {
    const field = e.target;
    const value = field.value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (value && !emailRegex.test(value)) {
        showFieldError(field, 'Por favor, insira um email válido');
    } else {
        clearFieldErrors(field);
    }
}

function showPasswordStrength(field, requirements) {
    clearFieldErrors(field);
    
    const failedRequirements = requirements.filter(req => !req.test);
    
    if (failedRequirements.length > 0) {
        const messages = failedRequirements.map(req => req.message);
        showFieldError(field, messages.join('<br>'));
    }
}

function showFieldError(field, message) {
    clearFieldErrors(field);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'text-danger small mt-1 field-error';
    errorDiv.innerHTML = message;
    
    field.parentNode.appendChild(errorDiv);
    field.classList.add('is-invalid');
}

function clearFieldErrors(field) {
    const errors = field.parentNode.querySelectorAll('.field-error');
    errors.forEach(error => error.remove());
    field.classList.remove('is-invalid');
}

// Função para mostrar notificações toast
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    document.getElementById('toast-container').appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast do DOM após ser escondido
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Função para confirmar ações
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Utilitários gerais
const Utils = {
    // Formatar CPF
    formatCPF: function(cpf) {
        return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    },
    
    // Formatar CNPJ
    formatCNPJ: function(cnpj) {
        return cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
    },
    
    // Formatar telefone
    formatPhone: function(phone) {
        const cleaned = phone.replace(/\D/g, '');
        if (cleaned.length === 11) {
            return cleaned.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
        } else if (cleaned.length === 10) {
            return cleaned.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
        }
        return phone;
    },
    
    // Debounce para otimizar eventos
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Tornar funções disponíveis globalmente
window.showToast = showToast;
window.confirmAction = confirmAction;
window.Utils = Utils;