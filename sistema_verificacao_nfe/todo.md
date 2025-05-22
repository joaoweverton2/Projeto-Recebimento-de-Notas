# Lista de Tarefas para o Sistema de Verificação de Notas Fiscais

## Análise e Preparação
- [x] Analisar a estrutura do arquivo "Base de notas.xlsx"
- [x] Projetar o fluxo de validação e resposta em Python
- [x] Definir a estrutura do projeto (arquivos e diretórios)

## Desenvolvimento Backend (Python)
- [x] Criar função para carregar e processar o arquivo Excel
- [x] Implementar lógica de validação dos campos (UF, Nfe, Pedido)
- [x] Desenvolver algoritmo para comparação de datas (mês/ano de planejamento vs. recebimento)
- [x] Criar função para gerar resposta ("Pode abrir JIRA" ou "Abrir JIRA após o fechamento do mês")
- [x] Implementar armazenamento dos dados digitalizados em CSV/XLS

## Desenvolvimento Frontend (Interface Web)
- [x] Criar estrutura básica da página web
- [x] Implementar formulário com campos obrigatórios (UF, Nfe, Pedido, Data de recebimento)
- [x] Adicionar validações de formulário no frontend
- [x] Desenvolver interface para exibição dos resultados
- [x] Estilizar a interface para melhor experiência do usuário

## Integração e Testes
- [x] Conectar frontend e backend
- [x] Testar validação dos campos com a base de dados
- [x] Verificar funcionamento da lógica de comparação de datas
- [x] Testar armazenamento dos dados em CSV/XLS
- [x] Realizar testes de usabilidade

## Finalização
- [ ] Documentar o código e o sistema
- [ ] Preparar instruções de uso e atualização
- [ ] Implantar a aplicação para acesso público
- [ ] Entregar o sistema completo ao usuário
