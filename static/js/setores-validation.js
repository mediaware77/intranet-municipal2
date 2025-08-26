// Validação de setores duplicados
document.addEventListener('DOMContentLoaded', function() {
    
    // Função para validar setores únicos
    function validarSetoresUnicos() {
        const setorPrincipal = document.getElementById('id_grupo_primario');
        const setoresSecundarios = document.getElementById('id_grupos_secundarios');
        
        if (!setorPrincipal || !setoresSecundarios) {
            return; // Campos não encontrados na página
        }
        
        function mostrarErro(elemento, mensagem) {
            // Remove erros anteriores
            const erroAnterior = elemento.parentNode.querySelector('.erro-setores');
            if (erroAnterior) {
                erroAnterior.remove();
            }
            
            // Adiciona novo erro
            const divErro = document.createElement('div');
            divErro.className = 'erro-setores text-danger small mt-1';
            divErro.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i>${mensagem}`;
            elemento.parentNode.appendChild(divErro);
            
            // Adiciona classe de erro ao campo
            elemento.classList.add('is-invalid');
        }
        
        function removerErro(elemento) {
            const erro = elemento.parentNode.querySelector('.erro-setores');
            if (erro) {
                erro.remove();
            }
            elemento.classList.remove('is-invalid');
        }
        
        function validar() {
            const valorPrincipal = setorPrincipal.value;
            const valoresSecundarios = Array.from(setoresSecundarios.selectedOptions).map(option => option.value);
            
            // Remove erros anteriores
            removerErro(setoresSecundarios);
            
            if (valorPrincipal && valoresSecundarios.includes(valorPrincipal)) {
                const nomeSetor = setorPrincipal.selectedOptions[0]?.text || 'setor selecionado';
                mostrarErro(
                    setoresSecundarios,
                    `O setor "${nomeSetor}" já está selecionado como principal. Não pode ser selecionado também nos setores secundários.`
                );
                return false;
            }
            
            return true;
        }
        
        // Eventos de validação
        setorPrincipal.addEventListener('change', validar);
        setoresSecundarios.addEventListener('change', validar);
        
        // Validação no envio do formulário
        const form = setorPrincipal.closest('form');
        if (form) {
            form.addEventListener('submit', function(e) {
                if (!validar()) {
                    e.preventDefault();
                    
                    // Scroll até o erro
                    const erro = document.querySelector('.erro-setores');
                    if (erro) {
                        erro.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    
                    // Mostra toast de erro
                    if (typeof showToast !== 'undefined') {
                        showToast('Por favor, corrija os erros nos setores antes de continuar.', 'danger');
                    }
                }
            });
        }
        
        // Melhoria visual: destaca o setor principal nos secundários
        function destacarSetorPrincipal() {
            const valorPrincipal = setorPrincipal.value;
            
            Array.from(setoresSecundarios.options).forEach(option => {
                option.classList.remove('setor-principal-destacado');
                if (option.value === valorPrincipal && valorPrincipal) {
                    option.classList.add('setor-principal-destacado');
                    option.style.backgroundColor = '#fff3cd';
                    option.style.color = '#856404';
                    option.style.fontWeight = 'bold';
                } else {
                    option.style.backgroundColor = '';
                    option.style.color = '';
                    option.style.fontWeight = '';
                }
            });
        }
        
        setorPrincipal.addEventListener('change', destacarSetorPrincipal);
        destacarSetorPrincipal(); // Executa na inicialização
    }
    
    // Inicializa a validação
    validarSetoresUnicos();
    
    // Função para auto-remover setor principal dos secundários
    function autoRemoverDuplicados() {
        const setorPrincipal = document.getElementById('id_grupo_primario');
        const setoresSecundarios = document.getElementById('id_grupos_secundarios');
        
        if (!setorPrincipal || !setoresSecundarios) return;
        
        setorPrincipal.addEventListener('change', function() {
            const valorPrincipal = this.value;
            if (!valorPrincipal) return;
            
            // Remove o setor principal dos secundários automaticamente
            Array.from(setoresSecundarios.options).forEach(option => {
                if (option.value === valorPrincipal && option.selected) {
                    option.selected = false;
                    
                    // Mostra notificação amigável
                    if (typeof showToast !== 'undefined') {
                        showToast(
                            `O setor "${option.text}" foi removido dos setores secundários pois já está definido como principal.`,
                            'info'
                        );
                    }
                }
            });
        });
    }
    
    // Inicializa auto-remoção
    autoRemoverDuplicados();
});