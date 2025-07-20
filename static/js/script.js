document.addEventListener('DOMContentLoaded', function() {
    // Elementos do DOM
    const nfeForm = document.getElementById('nfeForm');
    const resultSection = document.getElementById('resultSection');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultContent = document.getElementById('resultContent');
    const newVerificationBtn = document.getElementById('newVerificationBtn');
    
    // Configurar data máxima como hoje
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('data_recebimento').setAttribute('max', today);
    
    // Função de validação do formulário
    function validateForm() {
        let isValid = true;
        const ufPattern = /^[A-Z]{2}(-[A-Z]{2,3})?$/;
        
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
        
        // Mostrar loading e esconder resultados
        resultSection.style.display = 'block';
        loadingIndicator.style.display = 'flex';
        resultContent.style.display = 'none';
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
            
            const data = await response.json();
            loadingIndicator.style.display = 'none';
            
            // Preencher resultados
            document.getElementById('result-uf').textContent = data.uf;
            document.getElementById('result-nfe').textContent = data.nfe;
            document.getElementById('result-pedido').textContent = data.pedido;
            document.getElementById('result-data').textContent = formatarDataRecebimento(data.data_recebimento);
            document.getElementById('result-planejamento').textContent = data.data_planejamento;
            document.getElementById('result-decisao').textContent = data.decisao;
            
            // Configurar ícone e título
            const resultIcon = document.getElementById('resultIcon');
            const resultTitle = document.getElementById('resultTitle');
            
            if (data.valido) {
                if (data.decisao.includes('Pode abrir')) {
                    resultIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
                    resultTitle.textContent = 'Verificação Concluída';
                    document.getElementById('result-decisao').className = 'decision success';
                } else {
                    resultIcon.innerHTML = '<i class="fas fa-clock"></i>';
                    resultTitle.textContent = 'Verificação Concluída';
                    document.getElementById('result-decisao').className = 'decision warning';
                }
            } else {
                resultIcon.innerHTML = '<i class="fas fa-exclamation-circle"></i>';
                resultTitle.textContent = 'Nota não encontrada';
                document.getElementById('result-decisao').className = 'decision error';
            }
            
            resultContent.style.display = 'block';
            
        } catch (error) {
            loadingIndicator.style.display = 'none';
            resultContent.style.display = 'block';
            
            // Preencher com dados do formulário em caso de erro
            document.getElementById('result-uf').textContent = document.getElementById('uf').value.trim().toUpperCase();
            document.getElementById('result-nfe').textContent = document.getElementById('nfe').value.trim();
            document.getElementById('result-pedido').textContent = document.getElementById('pedido').value.trim();
            document.getElementById('result-data').textContent = formatarDataRecebimento(document.getElementById('data_recebimento').value);
            document.getElementById('result-planejamento').textContent = '';
            document.getElementById('result-decisao').textContent = 'Entre em contato com os analistas do PCM';
            
            const resultIcon = document.getElementById('resultIcon');
            const resultTitle = document.getElementById('resultTitle');
            resultIcon.innerHTML = '<i class="fas fa-exclamation-circle"></i>';
            resultTitle.textContent = 'Erro no servidor';
            document.getElementById('result-decisao').className = 'decision error';
        }
    });
    
    // Botão para nova verificação
    newVerificationBtn.addEventListener('click', function() {
        nfeForm.reset();
        resultSection.style.display = 'none';
        document.querySelector('.form-section').scrollIntoView({ behavior: 'smooth' });
    });
});