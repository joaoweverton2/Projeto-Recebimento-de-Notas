import os
import sys
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

# Adiciona o diretório do projeto ao path
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

from database import DatabaseManager

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

def force_migration():
    logger.info("Iniciando script de migração de dados para Google Sheets.")

    try:
        # Inicializa o DatabaseManager
        db_manager = DatabaseManager()
        
        # Verifica se a conexão foi estabelecida corretamente
        if db_manager.worksheet is None:
            logger.error("Falha ao conectar ao Google Sheets. Verifique:")
            logger.error("1. Se as variáveis de ambiente GOOGLE_CREDENTIALS_BASE64 e GOOGLE_SHEET_ID estão configuradas")
            logger.error("2. Se a planilha existe e a conta de serviço tem permissão")
            return

        worksheet = db_manager.worksheet
        sheet_id_log = os.getenv("GOOGLE_SHEET_ID", "N/A")
        logger.info(f"Conectado à planilha Google Sheets: {sheet_id_log}, aba: {worksheet.title}")

        # Define o caminho do arquivo Excel
        excel_file_paths = [
            project_dir / 'data' / 'Base_de_notas.xlsx',
            Path(os.getcwd()) / 'data' / 'Base_de_notas.xlsx',
            Path('/') / 'opt' / 'render' / 'project' / 'src' / 'data' / 'Base_de_notas.xlsx'
        ]
        
        data_file = None
        for path in excel_file_paths:
            if path.exists():
                data_file = path
                break
        
        if not data_file:
            logger.error("Arquivo Base_de_notas.xlsx não encontrado nos caminhos: %s", excel_file_paths)
            return
        
        logger.info(f"Arquivo Excel encontrado: {data_file}")
        
        # Carrega os dados do Excel
        try:
            df = pd.read_excel(data_file, engine='openpyxl')
            logger.info(f"Carregados {len(df)} registros do Excel")
        except Exception as e:
            logger.error(f"Erro ao ler arquivo Excel: {str(e)}")
            return

        # Remove duplicatas
        df = df.drop_duplicates(subset=['uf', 'nfe', 'pedido'], keep='first')
        logger.info(f"Após remoção de duplicatas: {len(df)} registros")
        
        # Obtém dados existentes
        try:
            existing_data = worksheet.get_all_records()
            existing_keys = {(str(r['uf']).upper(), str(r['nfe']), str(r['pedido'])) for r in existing_data}
            logger.info(f"{len(existing_keys)} registros existentes no Google Sheets")
        except Exception as e:
            logger.error(f"Erro ao ler dados existentes: {str(e)}")
            return

        imported_count = 0
        for _, row in df.iterrows():
            try:
                uf = str(row['uf']).upper()
                nfe = str(row['nfe'])
                pedido = str(row['pedido'])
                current_key = (uf, nfe, pedido)
                
                if current_key in existing_keys:
                    logger.debug(f"Registro existente: UF={uf}, NFe={nfe}, Pedido={pedido}")
                    continue

                # Prepara os dados
                registro = {
                    'uf': uf,
                    'nfe': nfe,
                    'pedido': pedido,
                    'data_recebimento': pd.to_datetime(row['data_recebimento']).strftime('%Y-%m-%d'),
                    'valido': 'TRUE' if row.get('valido', True) else 'FALSE',
                    'data_planejamento': pd.to_datetime(row['data_planejamento']).strftime('%Y-%m-%d') if pd.notna(row.get('data_planejamento')) else '',
                    'decisao': str(row.get('decisao', '')) if pd.notna(row.get('decisao')) else '',
                    'mensagem': str(row.get('mensagem', '')) if pd.notna(row.get('mensagem')) else ''
                }

                # Usa o método criar_registro do DatabaseManager
                result = db_manager.criar_registro(registro)
                if result:
                    imported_count += 1
                    logger.info(f"Registro importado: UF={uf}, NFe={nfe}, Pedido={pedido}")
                else:
                    logger.warning(f"Falha ao importar registro: UF={uf}, NFe={nfe}, Pedido={pedido}")
                    
            except Exception as e:
                logger.error(f"Erro no registro UF={row.get('uf')}, NFe={row.get('nfe')}: {str(e)}")
                continue
        
        logger.info(f"Migração concluída: {imported_count} novos registros importados")
                
    except Exception as e:
        logger.error(f"Erro fatal durante a migração: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    force_migration()