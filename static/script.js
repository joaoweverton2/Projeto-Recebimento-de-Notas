// Funções de validação e interação com o formulário
document.addEventListener('DOMContentLoaded', function() {
    const nfeForm = document.getElementById('nfeForm');
    const resultSection = document.getElementById('resultSection');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultContent = document.getElementById('resultContent');
    const errorContent = document.getElementById('errorContent');
    const newVerificationBtn = document.getElementById('newVerificationBtn');
    const tryAgainBtn = document.getElementById('tryAgainBtn');
    
    // Definir data máxima como hoje
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('data_recebimento').setAttribute('max', today);
    
    // Validação de campos
    function validateForm() {
        let isValid = true;
        
        // Validar UF
        const uf = document.getElementById('uf').value.trim().toUpperCase();
        const ufError = document.getElementById('uf-error');
        if (uf.length !== 2 || !/^[A-Z]{2}$/.test(uf)) {
            ufError.textContent = 'UF deve conter exatamente 2 letras';
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
            // Validação adicional para garantir que a data não está no futuro
            const selectedDate = new Date(dataRecebimento);
            const currentDate = new Date();
            if (selectedDate > currentDate) {
                dataError.textContent = 'A data não pode ser futura';
                isValid = false;
            } else {
                dataError.textContent = '';
            }
        }
        
        return isValid;
    }
    
    // Função para validar números
    window.validateNumber = function(input) {
        if (input.value < 0) {
            input.value = '';
        }
    };
    
    // Função para converter YYYY-MM-DD (input date) para DD/MM/YYYY (backend)
    function converterDataParaBackend(dataISO) {
        if (!dataISO) return '';
        const [ano, mes, dia] = dataISO.split('-');
        return `${dia}/${mes}/${ano}`;
    }
    
    // Função para formatar data para exibição
    function formatarDataParaExibicao(dataString) {
        if (!dataString) return '';
        // Se já estiver no formato DD/MM/YYYY, retorna sem alteração
        if (dataString.includes('/')) {
            return dataString;
        }
        // Se estiver no formato YYYY-MM-DD, converte
        const [ano, mes, dia] = dataString.split('-');
        return `${dia}/${mes}/${ano}`;
    }
    
    // Envio do formulário
    nfeForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }
        
        // Mostrar seção de resultado e indicador de carregamento
        resultSection.style.display = 'block';
        loadingIndicator.style.display = 'flex';
        resultContent.style.display = 'none';
        errorContent.style.display = 'none';
        
        // Rolar para a seção de resultado
        resultSection.scrollIntoView({ behavior: 'smooth' });
        
        // Obter e preparar os dados do formulário
        const formData = {
            uf: document.getElementById('uf').value.trim().toUpperCase(),
            nfe: document.getElementById('nfe').value.trim(),
            pedido: document.getElementById('pedido').value.trim(),
            data_recebimento: converterDataParaBackend(document.getElementById('data_recebimento').value)
        };
        
        // Enviar requisição para o backend como JSON
        fetch('/verificar', {
    	    method: 'POST',
    	    headers: {
        	'Content-Type': 'application/json',
        	'Accept': 'application/json'
    	    },
    	    body: JSON.stringify(formData)
	})
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro na resposta do servidor');
            }
            return response.json();
        })
        .then(data => {
            // Ocultar indicador de carregamento
            loadingIndicator.style.display = 'none';
            
            if (data.valido) {
                // Mostrar conteúdo de resultado
                resultContent.style.display = 'block';
                
                // Preencher dados do resultado
                document.getElementById('result-uf').textContent = data.uf;
                document.getElementById('result-nfe').textContent = data.nfe;
                document.getElementById('result-pedido').textContent = data.pedido;
                document.getElementById('result-data').textContent = formatarDataParaExibicao(data.data_recebimento);
                document.getElementById('result-planejamento').textContent = data.data_planejamento;
                
                const decisaoElement = document.getElementById('result-decisao');
                decisaoElement.textContent = data.decisao;
                
                // Configurar ícone e classe baseado na decisão
                const resultIcon = document.getElementById('resultIcon');
                const resultTitle = document.getElementById('resultTitle');
                
                if (data.decisao === 'Pode abrir JIRA') {
                    resultIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
                    resultTitle.textContent = 'Verificação Concluída - Pode Abrir JIRA';
                    decisaoElement.className = 'decision success';
                } else