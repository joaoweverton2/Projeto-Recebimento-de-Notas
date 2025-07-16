import os
import sys
import time
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from flask import Flask

# Configuração básica
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def initialize_flask_app():
    """Configuração mínima do Flask para contexto"""
    app = Flask(__name__)
    app.config.update({
        'GOOGLE_CREDENTIALS_BASE64': os.getenv('GOOGLE_CREDENTIALS_BASE64'),
        'GOOGLE_SHEET_ID': os.getenv('GOOGLE_SHEET_ID')
    })
    return app

def validate_dataframe(df):
    """Valida as colunas necessárias no DataFrame"""
    required_columns = {'uf', 'nfe', 'pedido', 'data_recebimento'}
    missing = required_columns - set(df.columns)
    if missing:
        logger.error(f"Colunas obrigatórias faltando: {missing}")
        return False
    return True

def process_excel_file(file_path):
    """Carrega e valida o arquivo Excel"""
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        
        # Verifica colunas obrigatórias
        if not validate_dataframe(df):
            return None
            
        # Limpeza básica dos dados
        df = df.drop_duplicates(subset=['uf', 'nfe', 'pedido'])
        df['uf'] = df['uf'].astype(str).str.upper().str.strip()
        df['nfe'] = df['nfe'].astype(str).str.strip()
        df['pedido'] = df['pedido'].astype(str).str.strip()
        
        # Preenche valores opcionais com padrão
        df['valido'] = df.get('valido', True)
        df['data_planejamento'] = df.get('data_planejamento', '')
        df['decisao'] = df.get('decisao', '')
        df['mensagem'] = df.get('mensagem', '')
        
        return df
        
    except Exception as e:
        logger.error(f"Erro ao processar arquivo Excel: {str(e)}")
        return None

def migrate_data():
    """Função principal de migração"""
    logger.info("Iniciando processo de migração")
    
    app = initialize_flask_app()
    
    with app.app_context():
        from database import DatabaseManager
        
        try:
            # 1. Conexão com Google Sheets
            logger.info("Inicializando conexão com Google Sheets...")
            db_manager = DatabaseManager(app)
            time.sleep(3)  # Espera para estabilização
            
            if not hasattr(db_manager, 'worksheet') or db_manager.worksheet is None:
                logger.error("Falha na conexão com Google Sheets")
                return False

            # 2. Carregar arquivo Excel
            data_path = Path('/opt/render/project/src/data/Base_de_notas.xlsx')
            if not data_path.exists():
                logger.error("Arquivo não encontrado em: %s", data_path)
                return False
                
            df = process_excel_file(data_path)
            if df is None:
                return False
                
            logger.info(f"Dados prontos para migração: {len(df)} registros válidos")

            # 3. Processar registros
            success_count = 0
            for _, row in df.iterrows():
                try:
                    registro = {
                        'uf': row['uf'],
                        'nfe': row['nfe'],
                        'pedido': row['pedido'],
                        'data_recebimento': row['data_recebimento'].strftime('%Y-%m-%d') if pd.notna(row['data_recebimento']) else '',
                        'valido': bool(row['valido']),
                        'data_planejamento': row['data_planejamento'].strftime('%Y-%m-%d') if pd.notna(row.get('data_planejamento')) else None,
                        'decisao': str(row['decisao']),
                        'mensagem': str(row['mensagem'])
                    }
                    
                    if db_manager.criar_registro(registro):
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"Erro no registro {row.get('nfe')}: {str(e)}")
                    continue

            logger.info(f"Migração concluída: {success_count}/{len(df)} registros processados")
            return True
            
        except Exception as e:
            logger.error(f"Erro fatal: {str(e)}", exc_info=True)
            return False

if __name__ == '__main__':
    if migrate_data():
        sys.exit(0)
    else:
        sys.exit(1)