# Instruções de Instalação e Uso

## Requisitos do Sistema

- Python 3.6 ou superior
- Bibliotecas Python: Flask, Pandas, Werkzeug
- Navegador web moderno

## Instalação

1. **Preparar o ambiente**:
   ```bash
   # Criar e ativar ambiente virtual (opcional, mas recomendado)
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   
   # Instalar dependências
   pip install flask pandas werkzeug
   ```

2. **Configurar a estrutura de diretórios**:
   ```bash
   # Criar diretórios necessários
   mkdir -p data uploads
   
   # Copiar a base de dados para o diretório data
   cp "Base de notas.xlsx" data/
   ```

## Execução

1. **Iniciar a aplicação**:
   ```bash
   # A partir do diretório raiz do projeto
   python src/main.py
   ```

2. **Acessar a aplicação**:
   - Abra o navegador e acesse: `http://localhost:5000`
   - Para a página de administração: `http://localhost:5000/admin`

## Uso Diário

1. **Verificação de Notas Fiscais**:
   - Preencha os campos UF, NFe, Pedido e Data de recebimento
   - Clique em "Verificar"
   - Visualize o resultado da verificação

2. **Atualização da Base de Dados**:
   - Acesse a página de administração
   - Faça upload do novo arquivo Excel
   - Clique em "Atualizar Base de Dados"

3. **Download de Registros**:
   - Acesse a página de administração
   - Clique em "Baixar Registros (Excel)"

## Manutenção

- **Backup Regular**: Faça backup periódico dos arquivos em `data/`
- **Logs**: Verifique os logs da aplicação para identificar possíveis problemas
- **Atualização**: Mantenha as bibliotecas Python atualizadas

## Solução de Problemas

- Se a aplicação não iniciar, verifique se todas as dependências estão instaladas
- Se ocorrerem erros na validação, verifique se a base de dados está correta
- Para problemas de permissão, verifique se o usuário tem acesso de escrita aos diretórios
