#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala a versão correta do Python primeiro
pyenv install 3.11.9 -s
pyenv global 3.11.9

# Depois instala as dependências
pip install --upgrade pip
pip install -r requirements.txt