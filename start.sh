#!/usr/bin/env bash

# Start Gunicorn with proper configuration for Render
echo "🚀 Iniciando aplicação Flask com Gunicorn..."

# Use a porta fornecida pelo Render ou 5000 como fallback
PORT=${PORT:-5000}

# Configurar variável Flask
export FLASK_APP=main.py

# Iniciar Gunicorn
exec gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 main:app

