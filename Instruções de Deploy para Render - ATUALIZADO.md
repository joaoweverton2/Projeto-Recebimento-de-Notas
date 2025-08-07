# Instruções de Deploy para Render - ATUALIZADO

## Problema Resolvido
O problema de reset do banco de dados `Base_de_notas.xlsx` no Render foi resolvido, garantindo a persistência das atualizações feitas na interface de ADMIN, utilizando Google Sheets para persistência.

## Arquivos Criados/Modificados

### 1. `build.sh` (NOVO)
Script de build que:
- Instala as dependências do `requirements.txt`
- Executa a migração de dados iniciais (agora para o Google Sheets)

### 2. `start.sh` (MODIFICADO)
Script de inicialização que:
- Inicia a aplicação usando Gunicorn
- Configura para usar a porta fornecida pelo Render ($PORT)

### 3. `database.py` (MODIFICADO)
- Adaptado para interagir com duas worksheets no Google Sheets: `registros_nf` e `Base_de_notas`.

### 4. `validacao_nfe.py` (MODIFICADO)
- Adaptado para usar o `DatabaseManager` para carregar os dados da `Base_de_notas` diretamente do Google Sheets.

### 5. `main.py` (MODIFICADO)
- Removida a dependência do arquivo local `Base_de_notas.xlsx`.
- O endpoint `/atualizar-base` agora lê o arquivo Excel enviado e o envia para a worksheet `Base_de_notas` no Google Sheets.

### 6. `migrate_data.py` (MODIFICADO)
- Adaptado para migrar tanto `registros_antigos.xlsx` quanto `Base_de_notas.xlsx` para as respectivas worksheets no Google Sheets durante o build/deploy inicial.

## Como Fazer o Deploy no Render

### Passo 1: Configuração no Render
1. Acesse o painel do Render
2. Conecte seu repositório GitHub com as alterações feitas.
3. Configure as seguintes opções:

**Build Command:**
```bash
chmod +x build.sh && ./build.sh
```

**Start Command:**
```bash
chmod +x start.sh && ./start.sh
```

**Environment:**
- Python Version: `3.11.9` (ou conforme seu `runtime.txt`)

### Passo 2: Variáveis de Ambiente
Você **DEVE** configurar as seguintes variáveis de ambiente no Render:

- `GOOGLE_CREDENTIALS_BASE64`: Suas credenciais de serviço do Google codificadas em Base64. (As mesmas que você já usa para `registros_nf`).
- `GOOGLE_SHEET_ID`: O ID da sua planilha do Google Sheets onde os dados serão armazenados. (A mesma que você já usa para `registros_nf`).

Certifique-se de que a conta de serviço associada às credenciais tenha permissão de leitura e escrita na planilha do Google Sheets.

### Passo 3: Deploy
1. Faça commit e push dos novos arquivos (`build.sh`, `start.sh` e as modificações nos arquivos `.py`)
2. O Render detectará as mudanças e iniciará o deploy automaticamente.
3. Monitore os logs para verificar se a migração inicial foi executada com sucesso e se a aplicação iniciou sem erros.

## Teste de Persistência
Após o deploy, siga estes passos para testar a persistência:

1. Acesse a interface de ADMIN da sua aplicação no Render (`/admin`).
2. Faça o upload de um novo arquivo `Base_de_notas.xlsx` com dados atualizados.
3. Verifique se a atualização foi bem-sucedida (a mensagem de sucesso deve aparecer).
4. **Importante:** Force um redeploy ou reinicie o serviço no Render (ou espere algumas horas para que o Render possa reiniciar o container automaticamente).
5. Após o reinício, acesse novamente a interface de ADMIN e verifique se os dados que você carregou persistem e não voltaram ao estado inicial.

Se os dados persistirem após o reinício, a solução funcionou!



