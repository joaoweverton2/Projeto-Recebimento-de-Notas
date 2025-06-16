# Instruções de Deploy para Render - ATUALIZADO

## Problema Resolvido
O erro "cannot access 'build.sh': No such file or directory" foi resolvido com a criação dos arquivos necessários para o deploy no Render.

## Arquivos Criados/Modificados

### 1. `build.sh` (NOVO)
Script de build que:
- Instala as dependências do `requirements.txt`
- Executa a migração de dados iniciais
- Prepara o ambiente para produção

### 2. `start.sh` (NOVO)
Script de inicialização que:
- Inicia a aplicação usando Gunicorn
- Configura para usar a porta fornecida pelo Render ($PORT)
- Usa 4 workers para melhor performance

### 3. Melhorias Anteriores
- Migração automática de dados iniciais
- Parser de datas melhorado
- Logs detalhados para troubleshooting

## Como Fazer o Deploy no Render

### Passo 1: Configuração no Render
1. Acesse o painel do Render
2. Conecte seu repositório GitHub
3. Configure as seguintes opções:

**Build Command:**
```bash
chmod +x build.sh && ./build.sh
```

**Start Command:**
```bash
./start.sh
```

**Environment:**
- Python Version: `3.11.9` (ou conforme seu `runtime.txt`)

### Passo 2: Variáveis de Ambiente (Opcional)
Se você estiver usando PostgreSQL no Render, a variável `DATABASE_URL` será configurada automaticamente.

### Passo 3: Deploy
1. Faça commit e push dos novos arquivos (`build.sh` e `start.sh`)
2. O Render detectará as mudanças e iniciará o deploy automaticamente
3. Monitore os logs para verificar se a migração foi executada com sucesso

## Logs Esperados Durante o Deploy

### Durante o Build:
```
--- Iniciando script de build ---
Instalando dependências...
Executando migração de dados iniciais...
Tabelas criadas/verificadas
Migração concluída: X registros importados
--- Script de build concluído ---
```

### Durante o Start:
```
📂 Diretório base: /opt/render/project/src
📝 Arquivo de notas: /opt/render/project/src/data/Base_de_notas.xlsx
🔍 Arquivo existe? True
🗄️ Banco de dados: postgresql://...
📊 Registros no banco: 87
✅ Banco já contém dados
```

## Troubleshooting

### Se o build falhar:
1. Verifique se os arquivos `build.sh` e `start.sh` estão no diretório raiz
2. Confirme que ambos têm permissão de execução (`chmod +x`)
3. Verifique os logs do Render para erros específicos

### Se a migração não funcionar:
1. Acesse o Shell do Render
2. Execute manualmente: `python migrate_data.py`
3. Verifique se o arquivo `data/registros.xlsx` existe

### Se a aplicação não iniciar:
1. Verifique se o Gunicorn está instalado (`requirements.txt`)
2. Confirme que o arquivo `main.py` existe
3. Verifique se a porta está configurada corretamente

## Estrutura Final do Projeto
```
Projeto-Recebimento-de-Notas/
├── build.sh              # Script de build (NOVO)
├── start.sh              # Script de inicialização (NOVO)
├── main.py               # Aplicação principal
├── database.py           # Gerenciador de banco (MELHORADO)
├── migrate_data.py       # Script de migração manual (NOVO)
├── requirements.txt      # Dependências
├── runtime.txt           # Versão do Python
├── data/
│   ├── registros.xlsx    # Dados iniciais
│   └── Base_de_notas.xlsx
├── templates/
├── static/
└── ...
```

Agora o projeto está completamente preparado para deploy no Render!

