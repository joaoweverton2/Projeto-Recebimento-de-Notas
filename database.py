"""
database.py - Módulo completo para gerenciamento do banco de dados SQLite
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = 'data/registros.db'):
        """
        Inicializa o gerenciador do banco de dados com tratamento completo.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Retorna uma conexão com o banco de dados."""
        return sqlite3.connect(self.db_path)
    
    def _initialize_db(self) -> None:
        """Inicializa o banco com a estrutura correta."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uf TEXT NOT NULL,
                    nfe INTEGER NOT NULL,
                    pedido INTEGER NOT NULL,
                    data_recebimento TEXT NOT NULL,
                    valido BOOLEAN NOT NULL,
                    data_planejamento TEXT,
                    decisao TEXT,
                    mensagem TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def import_from_excel(self, excel_path: str) -> bool:
        """
        Importa dados do arquivo Excel para o SQLite com tratamento completo.
        """
        try:
            # Carrega o arquivo Excel
            df = pd.read_excel(excel_path)
            
            # Verifica colunas obrigatórias
            required_cols = ['uf', 'nfe', 'pedido', 'data_recebimento']
            if not all(col in df.columns for col in required_cols):
                raise ValueError("Colunas obrigatórias faltantes no Excel")
            
            # Preenche colunas opcionais se não existirem
            if 'valido' not in df.columns:
                df['valido'] = True
            if 'timestamp' not in df.columns:
                df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Converte tipos de dados
            df['nfe'] = df['nfe'].astype(int)
            df['pedido'] = df['pedido'].astype(int)
            df['valido'] = df['valido'].astype(bool)
            
            # Formata datas
            df['data_recebimento'] = pd.to_datetime(df['data_recebimento']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            with self._get_connection() as conn:
                # Remove dados existentes para evitar duplicação
                cursor = conn.cursor()
                cursor.execute("DELETE FROM registros")
                
                # Importa os dados
                df.to_sql('registros', conn, if_exists='append', index=False)
                conn.commit()
                
                logger.info(f"Importados {len(df)} registros do Excel")
                return True
                
        except Exception as e:
            logger.error(f"Erro na importação do Excel: {str(e)}")
            return False
    
    def get_record_count(self) -> int:
        """Retorna o número total de registros na tabela."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM registros")
            return cursor.fetchone()[0]

# Teste da importação
if __name__ == "__main__":
    db = DatabaseManager()
    
    # Caminho para o arquivo Excel (ajuste conforme necessário)
    excel_path = Path('data/registros.xlsx')
    
    if excel_path.exists():
        print("Importando dados do Excel...")
        if db.import_from_excel(excel_path):
            print(f"Total de registros importados: {db.get_record_count()}")
        else:
            print("Falha na importação. Verifique os logs.")
    else:
        print(f"Arquivo Excel não encontrado em: {excel_path}")