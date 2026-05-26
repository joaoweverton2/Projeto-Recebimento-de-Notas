
import pandas as pd
import sqlite3
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SQLiteManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS base_notas (
                    UF TEXT,
                    Nfe INTEGER,
                    Pedido INTEGER,
                    Planejamento TEXT,
                    Demanda TEXT
                )
            """)
            conn.commit()
            logger.info("Tabela 'base_notas' verificada/criada no SQLite.")
        except sqlite3.Error as e:
            logger.error(f"Erro ao criar tabela SQLite: {e}")
        finally:
            if conn:
                conn.close()

    def get_base_notas_data(self) -> pd.DataFrame:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM base_notas", conn)
            return df
        except sqlite3.Error as e:
            logger.error(f"Erro ao ler dados da base_notas do SQLite: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    def update_base_notas_data(self, df: pd.DataFrame):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            df.to_sql("base_notas", conn, if_exists="replace", index=False)
            conn.commit()
            logger.info("Tabela 'base_notas' atualizada no SQLite com sucesso.")
        except sqlite3.Error as e:
            logger.error(f"Erro ao atualizar base_notas no SQLite: {e}")
        finally:
            if conn:
                conn.close()

    def buscar_nota_sqlite(self, uf: str, nfe: int, pedido: int) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM base_notas WHERE UF = ? AND Nfe = ? AND Pedido = ?", 
                           (uf.upper(), nfe, pedido))
            columns = [description[0] for description in cursor.description]
            result = cursor.fetchone()
            if result:
                return [dict(zip(columns, result))]
            return []
        except sqlite3.Error as e:
            logger.error(f"Erro ao buscar nota no SQLite: {e}")
            return []
        finally:
            if conn:
                conn.close()
