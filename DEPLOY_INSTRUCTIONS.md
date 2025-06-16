# Instruções de Deploy para Render

## Problema Identificado
O projeto não estava carregando os dados iniciais da planilha `registros.xlsx` durante o deploy no Render devido a problemas de caminho de arquivo.

## Soluções Implementadas

### 1. Melhoria na Busca de Arquivos Legados
- Modificada a função `_find_legacy_file()` no `database.py` para usar caminhos absolutos baseados no diretório do projeto
- Adicionados logs detalhados para rastreamento da migração

### 2. Migração Automática no Startup
- Adicionada verificação automática no `main.py` que força a migração se o banco estiver vazio
- Logs informativos durante o processo de inicialização

### 3. Script de Migração Manual
- Criado `migrate_data.py` para forçar a migração manualmente se necessário

## Como Usar no Render

### Opção 1: Deploy Normal (Recomendado)
1. Faça commit e push das alterações
2. O sistema agora detecta automaticamente se o banco está vazio e carrega os dados iniciais

### Opção 2: Migração Manual (Se necessário)
Se por algum motivo a migração automática não funcionar:

1. No painel do Render, vá em "Shell" do seu serviço
2. Execute: `python migrate_data.py`

### Opção 3: Comando Flask CLI
Você também pode usar os comandos CLI do Flask:
```bash
flask db-init    # Inicializa o banco
flask db-reset   # Reseta o banco (cuidado!)
```

## Arquivos Modificados
- `database.py`: Melhorias na busca de arquivos e migração
- `main.py`: Adicionada verificação automática na inicialização
- `migrate_data.py`: Novo script para migração manual

## Verificação
Após o deploy, verifique os logs do Render para confirmar que a migração foi executada com sucesso. Você deve ver mensagens como:
- "Arquivo legado encontrado em: ..."
- "Migração concluída: X registros importados"

