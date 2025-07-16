import os
import sys
import time
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from flask import Flask

# Configuração de caminhos
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

def initialize_flask_app():
    """Cria uma instância mínima do Flask para contexto"""
    app = Flask(__name__)
    app.config.update({
        'GOOGLE_CREDENTIALS_BASE64': os.getenv('GOOGLE_CREDENTIALS_BASE64'),
        'GOOGLE_SHEET_ID': os.getenv('GOOGLE_SHEET_ID')
    })
    return app

def verify_google_sheets_connection(db_manager):
    """Verifica e valida a conexão com o Google Sheets"""
    if not hasattr(db_manager, 'worksheet') or db_manager.worksheet is None:
        logger.error("Conexão com Google Sheets falhou. Status:")
        logger.error(f"gc inicializado: {hasattr(db_manager, 'gc') and db_manager.gc is not None}")
        logger.error(f"spreadsheet: {hasattr(db_manager, 'spreadsheet') and db_manager.spreadsheet is not None}")
        logger.error(f"worksheet: {hasattr(db_manager, 'worksheet') and db_manager.worksheet is not None}")
        return False
    
    try:
        # Testa o acesso à planilha
        db_manager.worksheet.row_count
        return True
    except Exception as e:
        logger.error(f"Falha ao acessar worksheet: {str(e)}")
        return False

def find_data_file():
    """Localiza o arquivo de dados em vários caminhos possíveis"""
    possible_paths = [
        project_dir / 'data' / 'Base_de_notas.xlsx',
        Path(os.getcwd()) / 'data' / 'Base_de_notas.xlsx',
        Path('/opt/render/project/src/data/Base_de_notas.xlsx'),
        Path('/tmp/data/Base_de_notas.xlsx')
    ]
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"Arquivo encontrado em: {path}")
            return path
    
    logger.error("Arquivo não encontrado nos caminhos: %s", possible_paths)
    return None

def process_excel_data(data_file):
    """Processa o arquivo Excel e retorna um DataFrame limpo"""
    try:
        df = pd.read_excel(data_file, engine='openpyxl')
        logger.info(f"Dados carregados: {len(df)} registros")
        
        # Limpeza de dados
        df = df.drop_duplicates(subset=['uf', 'nfe', 'pedido'], keep='first')
        df['uf'] = df['uf'].astype(str).str.upper()
        df['nfe'] = df['nfe'].astype(str)
        df['pedido'] = df['pedido'].astype(str)
        
        return df
    except Exception as e:
        logger.error(f"Erro ao processar Excel: {str(e)}")
        return None

def migrate_data():
    """Função principal para migração de dados"""
    logger.info("Iniciando processo de migração")
    
    app = initialize_flask_app()
    
    with app.app_context():
        from database import DatabaseManager
        
        try:
            # Inicializa com delay para garantir conexão
            logger.info("Inicializando DatabaseManager...")
            db_manager = DatabaseManager(app)
            time.sleep(3)  # Espera para inicialização
            
            if not verify_google_sheets_connection(db_manager):
                return False

            # Localiza e processa arquivo
            data_file = find_data_file()
            if not data_file:
                return False
                
            df = process_excel_data(data_file)
            if df is None:
                return False

            # Obtém registros existentes
            existing_data = db_manager.worksheet.get_all_records()
            existing_keys = {
                (str(r['uf']).upper(), str(r['nfe']), str(r['pedido'])) 
                for r in existing_data
            }
            logger.info(f"Registros existentes: {len(existing_keys)}")

            # Processa cada registro
            success_count = 0
            for _, row in df.iterrows():
                try:
                    registro = {
                        'uf': row['uf'],
                        'nfe': row['nfe'],
                        'pedido': row['pedido'],
                        'data_recebimento': pd.to_datetime(row['data_recebimento']).strftime('%Y-%m-%d'),
                        'valido': bool(row.get('valido', True)),
                        'data_planejamento': pd.to_datetime(row['data_planejamento']).strftime('%Y-%m-%d') 
                            if pd.notna(row.get('data_planejamento')) else None,
                        'decisao': str(row.get('decisao', '')),
                        'mensagem': str(row.get('mensagem', ''))
                    }

                    if db_manager.criar_registro(registro):
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"Erro no registro {row.get('nfe')}: {str(e)}")
                    continue

            logger.info(f"Migração concluída: {success_count}/{len(df)} registros importados")
            return True
            
        except Exception as e:
            logger.error(f"Erro fatal: {str(e)}", exc_info=True)
            return False

if __name__ == '__main__':
    if migrate_data():
        sys.exit(0)
    else:
        sys.exit(1)