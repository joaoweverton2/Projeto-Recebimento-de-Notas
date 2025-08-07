#!/usr/bin/env bash

# Instala as dependências do requirements.txt
pip install -r requirements.txt

# Executa o script de migração de dados para o Google Sheets
python3.11 migrate_data.py


