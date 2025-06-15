#!/usr/bin/env bash
# exit on error
set -o errexit

# Verifica a versão do Python
echo "Python version: $(python 3.11.9)"

# Instala dependências
pip install --upgrade pip
pip install -r requirements.txt