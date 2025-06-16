#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Iniciando script de build ---"

# Instalar dependências
echo "Instalando dependências..."
pip install -r requirements.txt

# Executar migrações do banco de dados (se aplicável)
# Render geralmente executa migrações como parte do processo de build ou startup
# Se você usa Flask-Migrate, pode adicionar aqui:
# flask db upgrade

# Executar o script de migração de dados iniciais
echo "Executando migração de dados iniciais..."
python migrate_data.py

# Adicionar logs para verificar se os arquivos estão presentes
echo "Verificando estrutura de arquivos..."
ls -la
echo "Verificando pasta data..."
ls -la data/

echo "--- Script de build concluído ---"


