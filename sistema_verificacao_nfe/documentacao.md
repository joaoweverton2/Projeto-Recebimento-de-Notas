# Documentação do Sistema de Verificação de Notas Fiscais

## Visão Geral

O Sistema de Verificação de Notas Fiscais é uma aplicação web desenvolvida para automatizar o processo de verificação de notas fiscais e determinar se um chamado JIRA deve ser aberto imediatamente ou após o fechamento do mês. O sistema valida os dados informados pelo usuário contra uma base de dados e aplica regras de negócio específicas para gerar a resposta.

## Funcionalidades

1. **Verificação de Notas Fiscais**
   - Validação dos campos UF, NFe e Pedido contra a base de dados
   - Comparação de datas para determinar a abertura de JIRA
   - Exibição de resultado claro e visual para o usuário

2. **Armazenamento de Dados**
   - Registro de todas as verificações realizadas em CSV e Excel
   - Possibilidade de download dos registros para análise

3. **Administração**
   - Atualização da base de dados de notas fiscais
   - Download dos registros de verificações

## Estrutura do Projeto

```
projeto_nfe/
├── data/                      # Diretório para armazenamento de dados
│   ├── Base de notas.xlsx     # Base de dados de notas fiscais
│   ├── registros.csv          # Registros de verificações em CSV
│   └── registros.xlsx         # Registros de verificações em Excel
├── src/                       # Código-fonte da aplicação
│   ├── static/                # Arquivos estáticos
│   │   ├── css/               # Estilos CSS
│   │   │   └── styles.css     # Arquivo de estilos
│   │   └── js/                # Scripts JavaScript
│   │       └── script.js      # Script principal
│   ├── templates/             # Templates HTML
│   │   ├── admin.html         # Página de administração
│   │   └── index.html         # Página principal
│   └── main.py                # Aplicação Flask principal
├── uploads/                   # Diretório para uploads temporários
└── validacao_nfe.py           # Módulo de validação de notas fiscais
```

## Requisitos Técnicos

- Python 3.6 ou superior
- Flask (framework web)
- Pandas (manipulação de dados)
- Navegador web moderno

## Fluxo de Funcionamento

1. O usuário acessa a página principal do sistema
2. Preenche os campos obrigatórios (UF, NFe, Pedido, Data de recebimento)
3. O sistema valida se a combinação de UF, NFe e Pedido existe na base de dados
4. Se existir, o sistema obtém a data de planejamento e compara com a data de recebimento
5. Com base na comparação, determina se um JIRA deve ser aberto imediatamente ou após o fechamento do mês
6. O resultado é exibido para o usuário de forma clara e visual
7. Os dados da verificação são armazenados em CSV e Excel para consultas futuras

## Regras de Negócio

- **Validação de Dados**: A combinação de UF, NFe e Pedido deve existir na base de dados
- **Critério de Abertura de JIRA**: 
  - Se o mês e ano da data de planejamento forem menores ou iguais aos da data de recebimento, então "Pode abrir JIRA"
  - Caso contrário, "Abrir JIRA após o fechamento do mês"

## Instruções de Uso

### Para Usuários

1. Acesse a página principal do sistema
2. Preencha os campos obrigatórios:
   - UF: Unidade Federativa (ex: SP, RJ, MG)
   - NFe: Número da Nota Fiscal
   - Pedido: Número do Pedido
   - Data de Recebimento: Data em que a nota fiscal foi recebida
3. Clique no botão "Verificar"
4. Aguarde o processamento e visualize o resultado
5. Para realizar uma nova verificação, clique em "Nova Verificação"

### Para Administradores

1. Acesse a página de administração através do link "/admin"
2. Para atualizar a base de dados:
   - Selecione o arquivo Excel contendo a nova base de dados
   - Clique em "Atualizar Base de Dados"
3. Para baixar os registros de verificações:
   - Clique em "Baixar Registros (Excel)"

## Manutenção e Atualização

### Atualização da Base de Dados

A base de dados pode ser atualizada de duas formas:

1. **Via Interface Web**:
   - Acesse a página de administração (/admin)
   - Faça upload do novo arquivo Excel
   - Clique em "Atualizar Base de Dados"

2. **Manualmente**:
   - Substitua o arquivo "Base de notas.xlsx" no diretório "data"
   - Reinicie a aplicação se necessário

### Backup dos Registros

Recomenda-se fazer backup periódico dos arquivos de registros:
- data/registros.csv
- data/registros.xlsx

## Solução de Problemas

### Problemas Comuns

1. **Erro na validação dos campos**:
   - Verifique se os dados informados estão corretos
   - Confirme se a combinação de UF, NFe e Pedido existe na base de dados

2. **Erro ao atualizar a base de dados**:
   - Verifique se o arquivo está no formato Excel (.xlsx ou .xls)
   - Confirme se o arquivo possui as colunas necessárias (UF, Nfe, Pedido, Planejamento)

3. **Erro ao baixar registros**:
   - Verifique se existem registros no sistema
   - Confirme se o diretório "data" possui permissões de escrita

## Contato e Suporte

Para suporte técnico ou dúvidas sobre o sistema, entre em contato com o administrador responsável.
