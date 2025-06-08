"""
database.py - Versão corrigida com tratamento completo de importação/exportação
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, Any, List

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = 'data/registros.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()
        self._migrate_legacy_data()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
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

    def _migrate_legacy_data(self) -> None:
        """Migra dados do arquivo Excel legado para o SQLite"""
        legacy_path = Path('data/registros.xlsx')
        if legacy_path.exists():
            try:
                df = pd.read_excel(legacy_path)
                
                # Verifica e corrige a estrutura do DataFrame
                required_cols = ['uf', 'nfe', 'pedido', 'data_recebimento']
                if all(col in df.columns for col in required_cols):
                    # Preenche valores padrão para colunas opcionais
                    df['valido'] = df.get('valido', True)
                    df['data_planejamento'] = df.get('data_planejamento', '')
                    df['decisao'] = df.get('decisao', '')
                    df['mensagem'] = df.get('mensagem', '')
                    df['timestamp'] = pd.to_datetime(df.get('timestamp', datetime.now()))
                    
                    # Converte tipos
                    df['nfe'] = pd.to_numeric(df['nfe'], errors='coerce').astype('Int64')
                    df['pedido'] = pd.to_numeric(df['pedido'], errors='coerce').astype('Int64')
                    df = df.dropna(subset=['uf', 'nfe', 'pedido'])
                    
                    # Importa para o SQLite
                    with self._get_connection() as conn:
                        df.to_sql('registros', conn, if_exists='append', index=False)
                        conn.commit()
                    
                    # Renomeia o arquivo legado para evitar reimportação
                    legacy_path.rename(Path('data/registros_importados.xlsx'))
                    logger.info(f"Dados legados migrados: {len(df)} registros")
                
            except Exception as e:
                logger.error(f"Erro na migração de dados legados: {e}")

    def save_verification(self, data: Dict[str, Any]) -> bool:
        try:
            required = ['uf', 'nfe', 'pedido', 'data_recebimento', 'valido']
            if not all(field in data for field in required):
                raise ValueError("Campos obrigatórios faltando")
            
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO registros (
                        uf, nfe, pedido, data_recebimento, valido,
                        data_planejamento, decisao, mensagem, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(data['uf']),
                    int(data['nfe']),
                    int(data['pedido']),
                    str(data['data_recebimento']),
                    bool(data['valido']),
                    str(data.get('data_planejamento', '')),
                    str(data.get('decisao', '')),
                    str(data.get('mensagem', '')),
                    str(data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                ))
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Erro SQL: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao salvar: {e}")
            return False

    def export_to_excel(self, output_path: str) -> bool:
        try:
            with self._get_connection() as conn:
                # Query que replica exatamente a estrutura do arquivo original
                df = pd.read_sql("""
                    SELECT 
                        uf, nfe, pedido, data_recebimento,
                        valido, data_planejamento, decisao,
                        mensagem, timestamp
                    FROM registros
                    ORDER BY timestamp DESC
                """, conn)
                
                # Garante a ordem das colunas
                df = df[['uf', 'nfe', 'pedido', 'data_recebimento', 'valido',
                         'data_planejamento', 'decisao', 'mensagem', 'timestamp']]
                
                # Formatação consistente
                df['valido'] = df['valido'].astype(bool)
                df['data_recebimento'] = pd.to_datetime(df['data_recebimento'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                df.to_excel(output_path, index=False)
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Erro SQL na exportação: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro na exportação: {e}")
            return False

    def get_record_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM registros")
            return cursor.fetchone()[0]

# Teste da exportação
if __name__ == "__main__":
    db = DatabaseManager()
    print(f"Total de registros: {db.get_record_count()}")
    
    # Teste de exportação
    if db.export_to_excel('test_export.xlsx'):
        print("Exportação realizada com sucesso!")
    else:
        print("Falha na exportação")