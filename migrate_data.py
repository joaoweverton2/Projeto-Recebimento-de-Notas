"""
Script para forçar a migração de dados iniciais
Este script pode ser usado para garantir que os dados sejam carregados no deploy
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório do projeto ao path
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

from flask import Flask
from database import DatabaseManager, db, RegistroNF
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_migration():
    """Força a migração de dados iniciais."""
    app = Flask(__name__)
    
    # Configuração básica do banco
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        data_dir = project_dir / 'data'
        data_dir.mkdir(exist_ok=True)
        database_url = f'sqlite:///{data_dir}/registros.db'
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializa o banco
    db_manager = DatabaseManager(app)
    
    with app.app_context():
        try:
            # Cria as tabelas se não existirem
            db.create_all()
            logger.info("Tabelas criadas/verificadas")
            
            # Verifica se já existem dados
            count = RegistroNF.query.count()
            logger.info(f"Registros existentes no banco: {count}")
            
            if count == 0:
                logger.info("Banco vazio, forçando migração...")
                imported = db_manager._migrate_legacy_data()
                logger.info(f"Migração concluída: {imported} registros importados")
            else:
                logger.info("Banco já contém dados, migração não necessária")
                
        except Exception as e:
            logger.error(f"Erro durante a migração: {str(e)}")
            raise

if __name__ == '__main__':
    force_migration()

