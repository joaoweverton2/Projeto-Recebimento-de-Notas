#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 === INICIANDO BUILD PARA POSTGRESQL ==="

# Definir variável de ambiente Flask
export FLASK_APP=main.py

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Para PostgreSQL no Render, as migrações são importantes
echo "🗄️ Configurando banco de dados..."

# Verifica se existe pasta migrations
if [ -d "migrations" ]; then
    echo "📁 Pasta migrations encontrada, aplicando migrações..."
    flask db upgrade
else
    echo "📁 Pasta migrations não encontrada, inicializando..."
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
fi

# Executar o script de migração de dados iniciais
echo "📋 Executando migração de dados iniciais..."
python migrate_data.py

# Verificar estrutura de arquivos
echo "📂 Verificando estrutura de arquivos..."
echo "Arquivos na raiz:"
ls -la | head -10
echo ""
echo "Arquivos na pasta data:"
ls -la data/

echo "✅ === BUILD CONCLUÍDO ==="

