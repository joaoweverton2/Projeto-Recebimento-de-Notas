#!/usr/bin/env bash

# Limpa o cache do pip para garantir instalações limpas
pip cache purge

# Remove quaisquer pacotes relacionados ao PostgreSQL que possam ter sido instalados
pip uninstall -y psycopg2-binary Flask-SQLAlchemy Flask-Migrate SQLAlchemy alembic || true

# Instala as dependências do requirements.txt
pip install -r requirements.txt

# Executa o script de migração de dados
python3.11 migrate_data.py


