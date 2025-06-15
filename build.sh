#!/usr/bin/env bash
# exit on error
set -o errexit

# Verifica a versão do Python
echo "Python version: $(python 3.11.9)"

# Instala dependências com ordem específica para evitar conflitos
pip install --upgrade pip
pip install numpy==1.24.4  # Instala numpy primeiro
pip install -r requirements.txt