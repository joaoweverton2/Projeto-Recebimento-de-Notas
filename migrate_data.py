
import os
import sys
import pandas as pd
from pathlib import Path
import logging

# Adiciona o diretório do projeto ao path
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

from database import DatabaseManager # Importa o DatabaseManager para usar a conexão com o Google Sheets

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def force_migration():
    logger.info("Iniciando script de migração de dados para Google Sheets.")

    # Inicializa o DatabaseManager
    db_manager = DatabaseManager()
    
    try:
        # Verifica se a planilha 'registros_nf' existe e está acessível
        worksheet = db_manager.worksheet
        
        # Obtém o sheet_id diretamente da variável de ambiente para logging
        sheet_id_log = os.getenv("GOOGLE_SHEET_ID", "N/A")
        logger.info(f"Conectado à planilha Google Sheets: {sheet_id_log}, aba: {worksheet.title}")

        # Define o caminho do arquivo Excel
        # Tenta caminhos diferentes para compatibilidade local e Render
        excel_file_paths = [
            project_dir / 'data' / 'Base_de_notas.xlsx',
            Path(os.getcwd()) / 'data' / 'Base_de_notas.xlsx',
            Path('/') / 'opt' / 'render' / 'project' / 'src' / 'data' / 'Base_de_notas.xlsx' # Caminho comum no Render
        ]
        
        data_file = None
        for path in excel_file_paths:
            if path.exists():
                data_file = path
                break
        
        if not data_file:
            logger.error(f"❌ Arquivo Base_de_notas.xlsx não encontrado em nenhum dos caminhos esperados: {excel_file_paths}")
            return
        
        logger.info(f"📁 Arquivo Excel encontrado: {data_file}")
        
        # Carrega e processa os dados do Excel
        df = pd.read_excel(data_file, engine='openpyxl')
        logger.info(f"📋 Carregados {len(df)} registros do Excel")
        
        # Remove duplicatas com base em UF, NFe e Pedido
        df = df.drop_duplicates(subset=['uf', 'nfe', 'pedido'], keep='first')
        logger.info(f"📋 Após remoção de duplicatas: {len(df)} registros")
        
        # Lê os dados existentes na planilha do Google Sheets para evitar duplicatas
        existing_data = worksheet.get_all_records()
        existing_keys = set()
        for row in existing_data:
            key = (str(row.get('uf', '')).upper(), str(row.get('nfe', '')), str(row.get('pedido', '')))
            existing_keys.add(key)
        logger.info(f"📊 {len(existing_keys)} registros existentes no Google Sheets.")

        imported_count = 0
        for _, row in df.iterrows():
            try:
                # Prepara os dados para inserção
                uf = str(row['uf']).upper()
                nfe = str(row['nfe'])
                pedido = str(row['pedido'])
                
                # Cria uma chave única para verificar duplicatas
                current_key = (uf, nfe, pedido)
                
                if current_key in existing_keys:
                    logger.info(f"Registro já existe no Google Sheets, pulando: UF={uf}, NFe={nfe}, Pedido={pedido}")
                    continue

                # Formata a data de recebimento
                data_recebimento = pd.to_datetime(row['data_recebimento']).strftime('%d/%m/%Y')

                # Formata a data de planejamento, se existir
                data_planejamento = ''
                if pd.notna(row.get('data_planejamento')):
                    data_planejamento = pd.to_datetime(row['data_planejamento']).strftime('%d/%m/%Y')

                # Preenche valores padrão para colunas que podem estar faltando
                valido = 'TRUE' if row.get('valido', True) else 'FALSE'
                decisao = str(row.get('decisao', '')) if pd.notna(row.get('decisao')) else ''
                mensagem = str(row.get('mensagem', '')) if pd.notna(row.get('mensagem')) else ''

                # Adiciona o registro à planilha
                worksheet.append_row([
                    uf, nfe, pedido, data_recebimento, valido, data_planejamento, decisao, mensagem
                ])
                imported_count += 1
                logger.info(f"✅ Registro importado: UF={uf}, NFe={nfe}, Pedido={pedido}")
                
            except Exception as e:
                logger.error(f"⚠️ Erro ao processar registro {row.get('nfe', 'N/A')}: {e}")
                continue
        
        logger.info(f"✅ Migração concluída: {imported_count} novos registros importados para o Google Sheets.")
                
    except Exception as e:
        logger.error(f"❌ Erro durante a migração para Google Sheets: {str(e)}")
        raise

if __name__ == '__main__':
    force_migration()


