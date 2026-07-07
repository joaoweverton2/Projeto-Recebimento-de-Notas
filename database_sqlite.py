
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
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registros_nf (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uf TEXT,
                    nfe INTEGER,
                    pedido INTEGER,
                    data_recebimento TEXT,
                    data_planejamento TEXT,
                    decisao TEXT,
                    criado_em TEXT
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

    def salvar_registro_sqlite(self, data: Dict[str, Any]):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO registros_nf (uf, nfe, pedido, data_recebimento, data_planejamento, decisao, criado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data['uf'], data['nfe'], data['pedido'], data['data_recebimento'], 
                  data.get('data_planejamento', ''), data['decisao'], data['criado_em']))
            conn.commit()
            logger.info("Registro salvo no SQLite com sucesso.")
        except sqlite3.Error as e:
            logger.error(f"Erro ao salvar registro no SQLite: {e}")
        finally:
            if conn:
                conn.close()

    def listar_registros_sqlite(self) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT uf, nfe, pedido, data_recebimento, data_planejamento, decisao, criado_em FROM registros_nf ORDER BY criado_em DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Erro ao listar registros do SQLite: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def limpar_registros_sqlite(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM registros_nf")
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erro ao limpar registros no SQLite: {e}")
        finally:
            if conn:
                conn.close()
