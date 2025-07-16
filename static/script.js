document.addEventListener('DOMContentLoaded', function() {
    // Elementos do DOM
    const nfeForm = document.getElementById('nfeForm');
    const resultSection = document.getElementById('resultSection');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultContent = document.getElementById('resultContent');
    const errorContent = document.getElementById('errorContent');
    const newVerificationBtn = document.getElementById('newVerificationBtn');
    const tryAgainBtn = document.getElementById('tryAgainBtn');
    
    // Configurar data máxima como hoje
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('data_recebimento').setAttribute('max', today);
    
    // Função de validação do formulário
    function validateForm() {
        let isValid = true;
        const ufPattern = /^[A-Z]{2}(-[A-Z]{2,3})?$/; // Padrão para UF (ex: SP ou SP-ITV)
        
        // Validar UF
        const uf = document.getElementById('uf').value.trim().toUpperCase();
        const ufError = document.getElementById('uf-error');
        if (!uf || !ufPattern.test(uf)) {
            ufError.textContent = 'Formato inválido. Use: SP ou SP-ITV';
            isValid = false;
        } else {
            ufError.textContent = '';
        }
        
        // Validar NFe
        const nfe = document.getElementById('nfe').value.trim();
        const nfeError = document.getElementById('nfe-error');
        if (!nfe || isNaN(nfe) || parseInt(nfe) <= 0) {
            nfeError.textContent = 'Informe um número de NFe válido';
            isValid = false;
        } else {
            nfeError.textContent = '';
        }
        
        // Validar Pedido
        const pedido = document.getElementById('pedido').value.trim();
        const pedidoError = document.getElementById('pedido-error');
        if (!pedido || isNaN(pedido) || parseInt(pedido) <= 0) {
            pedidoError.textContent = 'Informe um número de pedido válido';
            isValid = false;
        } else {
            pedidoError.textContent = '';
        }
        
        // Validar Data de Recebimento
        const dataRecebimento = document.getElementById('data_recebimento').value;
        const dataError = document.getElementById('data-error');
        if (!dataRecebimento) {
            dataError.textContent = 'Informe a data de recebimento';
            isValid = false;
        } else {
            dataError.textContent = '';
        }
        
        return isValid;
    }
    
    // Função para validar números positivos
    window.validateNumber = function(input) {
        if (input.value < 0) {
            input.value = '';
        }
    };
    
    // Função para formatar data (DD/MM/YYYY)
    function formatarDataRecebimento(dataString) {
        if (!dataString) return '';
        const [ano, mes, dia] = dataString.split('-');
        return `${dia}/${mes}/${ano}`;
    }
    
    // Envio do formulário
    nfeForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }
        
        // Mostrar loading e esconder resultados/erros
        resultSection.style.display = 'block';
        loadingIndicator.style.display = 'flex';
        resultContent.style.display = 'none';
        errorContent.style.display = 'none';
        resultSection.scrollIntoView({ behavior: 'smooth' });
        
        try {
            // Preparar dados do formulário
            const formData = new URLSearchParams();
            formData.append('uf', document.getElementById('uf').value.trim().toUpperCase());
            formData.append('nfe', document.getElementById('nfe').value.trim());
            formData.append('pedido', document.getElementById('pedido').value.trim());
            formData.append('data_recebimento', document.getElementById('data_recebimento').value);
            
            // Enviar requisição
            const response = await fetch('/verificar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData
            });
            
            // Processar resposta
            const data = await response.json();
            loadingIndicator.style.display = 'none';
            
            if (!response.ok) {
                throw new Error(data.message || 'Erro na requisição ao servidor');
            }
            
            if (data.valido) {
                // Preencher resultados
                document.getElementById('result-uf').textContent = data.uf;
                document.getElementById('result-nfe').textContent = data.nfe;
                document.getElementById('result-pedido').textContent = data.pedido;
                document.getElementById('result-data').textContent = formatarDataRecebimento(data.data_recebimento);
                document.getElementById('result-planejamento').textContent = data.data_planejamento;
                
                const decisaoElement = document.getElementById('result-decisao');
                decisaoElement.textContent = data.decisao;
                
                // Configurar ícone e classe baseado na decisão
                const resultIcon = document.getElementById('resultIcon');
                const resultTitle = document.getElementById('resultTitle');
                
                if (data.decisao.includes('Pode abrir')) {
                    resultIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
                    resultTitle.textContent = 'Verificação Concluída - Pode Abrir JIRA';
                    decisaoElement.className = 'decision success';
                } else {
                    resultIcon.innerHTML = '<i class="fas fa-clock"></i>';
                    resultTitle.textContent = 'Verificação Concluída - Aguardar';
                    decisaoElement.className = 'decision warning';
                }
                
                resultContent.style.display = 'block';
            } else {
                // Mostrar erro
                errorContent.style.display = 'block';
                document.getElementById('errorMessage').textContent = data.mensagem || 'Nota fiscal não encontrada na base';
            }
        } catch (error) {
            // Tratar erros
            loadingIndicator.style.display = 'none';
            errorContent.style.display = 'block';
            document.getElementById('errorMessage').textContent = error.message || 'Erro ao processar a requisição';
            console.error('Erro:', error);
        }
    });
    
    // Botão para nova verificação
    newVerificationBtn.addEventListener('click', function() {
        nfeForm.reset();
        resultSection.style.display = 'none';
        document.querySelector('.form-section').scrollIntoView({ behavior: 'smooth' });
    });
    
    // Botão para tentar novamente
    tryAgainBtn.addEventListener('click', function() {
        resultSection.style.display = 'none';
        document.querySelector('.form-section').scrollIntoView({ behavior: 'smooth' });
    });
});