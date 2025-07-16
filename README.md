# Projeto de Recebimento de Notas Fiscais

Este projeto é uma aplicação Flask que permite verificar e registrar notas fiscais, utilizando o Google Sheets como banco de dados.

## Configuração Local

### Pré-requisitos

- Python 3.8+
- `pip` (gerenciador de pacotes Python)

### Instalação

1. Clone este repositório:
   ```bash
   git clone <URL_DO_SEU_REPOSITORIO>
   cd Projeto-Recebimento-de-Notas
   ```

2. Crie um ambiente virtual e ative-o (opcional, mas recomendado):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate  # Windows
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### Configuração do Google Sheets

Para que a aplicação funcione, você precisará configurar o acesso ao Google Sheets:

1. **Crie um projeto no Google Cloud Console e habilite a Google Sheets API:**
   - Vá para o [Google Cloud Console](https://console.cloud.google.com/).
   - Crie um novo projeto (ou selecione um existente).
   - No menu de navegação, vá para 'APIs e serviços' > 'Biblioteca'.
   - Procure por 'Google Sheets API' e habilite-a.

2. **Crie credenciais de serviço:**
   - No Google Cloud Console, vá para 'APIs e serviços' > 'Credenciais'.
   - Clique em 'Criar credenciais' > 'Conta de serviço'.
   - Siga as instruções para criar a conta de serviço. Dê a ela um nome descritivo.
   - Conceda à conta de serviço as permissões necessárias para acessar o Google Sheets (por exemplo, 'Editor' ou 'Proprietário' para o Google Sheet específico que você usará).

3. **Baixe o arquivo `credentials.json`:**
   - Após criar a conta de serviço, clique nela para ver os detalhes.
   - Vá para a aba 'Chaves' e clique em 'Adicionar chave' > 'Criar nova chave'.
   - Selecione 'JSON' como tipo de chave e clique em 'Criar'.
   - Um arquivo JSON será baixado. **Mantenha este arquivo SEGURO e NUNCA o adicione ao controle de versão (Git).**

4. **Compartilhe sua planilha do Google Sheets com a conta de serviço:**
   - Abra a planilha do Google Sheets que você deseja usar como banco de dados.
   - Clique em 'Compartilhar'.
   - Adicione o endereço de e-mail da conta de serviço (que você pode encontrar no arquivo `credentials.json` ou na página de detalhes da conta de serviço no Google Cloud Console) como um editor da planilha.

5. **Configure a variável de ambiente `GOOGLE_SHEET_ID`:**
   - Crie um arquivo `.env` na raiz do projeto (se ainda não existir).
   - Adicione a seguinte linha ao arquivo `.env`, substituindo `<SEU_GOOGLE_SHEET_ID>` pelo ID da sua planilha (encontrado na URL da planilha, entre `/d/` e `/edit`):
     ```
     GOOGLE_SHEET_ID=<SEU_GOOGLE_SHEET_ID>
     ```

6. **Configure a variável de ambiente `GOOGLE_CREDENTIALS_BASE64` para desenvolvimento local:**
   - **NUNCA adicione o arquivo `credentials.json` diretamente ao Git.**
   - Para uso local, você pode codificar o conteúdo do seu `credentials.json` em Base64 e adicioná-lo ao seu arquivo `.env`.
   - No seu terminal local, navegue até o diretório onde você salvou o `credentials.json` e execute:
     ```bash
     cat credentials.json | base64
     ```
   - Copie a saída completa deste comando e adicione ao seu arquivo `.env`:
     ```
     GOOGLE_CREDENTIALS_BASE64=<SUA_STRING_BASE64_AQUI>
     ```

7. **Adicione `credentials.json` e `.env` ao `.gitignore`:**
   - Crie ou edite o arquivo `.gitignore` na raiz do seu projeto e adicione as seguintes linhas para evitar que arquivos sensíveis sejam versionados:
     ```
     credentials.json
     .env
     ```

### Execução

Para iniciar a aplicação localmente:

```bash
python main.py
```

A aplicação estará disponível em `http://127.0.0.1:5000`.

## Deploy no Render

### Pré-requisitos

- Uma conta no [Render](https://render.com/)
- Um repositório GitHub com este projeto (você precisará fazer o push do seu código para o GitHub primeiro)

### Passos para o Deploy

1. **Crie um novo Web Service no Render:**
   - Faça login no Render e clique em 'New' > 'Web Service'.
   - Conecte sua conta GitHub e selecione o repositório onde você fez o push deste projeto.

2. **Configurações do Web Service:**
   - **Name:** Escolha um nome para o seu serviço (ex: `notas-fiscais-app`)
   - **Region:** Escolha a região mais próxima dos seus usuários.
   - **Branch:** `main` (ou a branch que você estiver usando)
   - **Root Directory:** `/` (se o seu `main.py` estiver na raiz do repositório)
   - **Runtime:** `Python 3`
   - **Build Command:** `bash build.sh` (Este script irá limpar dependências antigas e instalar as novas)
   - **Start Command:** `python main.py`

3. **Variáveis de Ambiente (Environment Variables):**
   - No Render, vá para a seção 'Environment' do seu Web Service.
   - **CRÍTICO:** Certifique-se de que **NÃO EXISTE** nenhuma variável de ambiente relacionada ao PostgreSQL (ex: `DATABASE_URL`, `SQLALCHEMY_DATABASE_URI`). Remova-as se existirem.
   - Adicione as seguintes variáveis de ambiente:
     - **Key:** `GOOGLE_SHEET_ID`
     - **Value:** O ID da sua planilha do Google Sheets.
     - **Key:** `GOOGLE_CREDENTIALS_BASE64`
     - **Value:** A string Base64 do seu `credentials.json` (obtida no passo 6 da Configuração do Google Sheets para desenvolvimento local).

4. **Deploy:**
   - **CRÍTICO:** Antes de iniciar o deploy, vá para a seção 'Deploys' do seu Web Service no Render e clique em 'Clear build cache & Deploy' (ou uma opção similar para limpar o cache de build).
   - Clique em 'Create Web Service' (se for o primeiro deploy) ou 'Deploy latest commit' (se já existir).
   - Acompanhe os logs para garantir que o deploy seja bem-sucedido.


