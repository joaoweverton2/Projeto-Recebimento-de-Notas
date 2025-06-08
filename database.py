"""
database.py - Módulo para gerenciamento do banco de dados SQLite
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = 'data/registros.db'):
        """
        Inicializa o gerenciador do banco de dados.
        
        Args:
            db_path: Caminho para o arquivo do banco de dados SQLite.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Inicializa o banco de dados e cria as tabelas se não existirem."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela de registros de verificação
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uf TEXT NOT NULL,
                    nfe INTEGER NOT NULL,
                    pedido INTEGER NOT NULL,
                    data_recebimento TEXT NOT NULL,
                    valido INTEGER NOT NULL,
                    data_planejamento TEXT,
                    decisao TEXT,
                    mensagem TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.commit()

    def _get_connection(self):
        """Retorna uma conexão com o banco de dados."""
        return sqlite3.connect(self.db_path)

    def import_from_excel(self, excel_path: str) -> bool:
        """
        Importa dados de um arquivo Excel para o banco de dados.
        
        Args:
            excel_path: Caminho para o arquivo Excel.
            
        Returns:
            True se a importação foi bem-sucedida, False caso contrário.
        """
        try:
            df = pd.read_excel(excel_path)
            
            # Converter colunas para os tipos corretos
            df['valido'] = df['valido'].astype(int)
            
            with self._get_connection() as conn:
                df.to_sql('registros', conn, if_exists='append', index=False)
            
            logger.info(f"Dados importados com sucesso de {excel_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao importar dados do Excel: {e}")
            return False

    def save_verification(self, data: Dict[str, Any]) -> bool:
        """
        Salva um registro de verificação no banco de dados.
        
        Args:
            data: Dicionário com os dados da verificação.
            
        Returns:
            True se o salvamento foi bem-sucedido, False caso contrário.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                                
                cursor.execute("""
                    INSERT INTO registros (
                        uf, nfe, pedido, data_recebimento, valido,
                        data_planejamento, decisao, mensagem, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['uf'],
                    int(data['nfe']),
                    int(data['pedido']),
                    data['data_recebimento'],
                    int(data['valido']),
                    data.get('data_planejamento', ''),
                    data.get('decisao', ''),
                    data.get('mensagem', ''),
                    data.get('timestamp', '')
                ))
                
                conn.commit()
            
            logger.info("Registro salvo com sucesso no banco de dados")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar registro: {e}")
            return False

    def export_to_excel(self, output_path: str) -> bool:
        """
        Exporta os registros do banco de dados para um arquivo Excel.
        
        Args:
            output_path: Caminho para o arquivo Excel de saída.
            
        Returns:
            True se a exportação foi bem-sucedida, False caso contrário.
        """
        try:
            with self._get_connection() as conn:
                df = pd.read_sql("SELECT * FROM registros", conn)
                df.to_excel(output_path, index=False)
            
            logger.info(f"Dados exportados com sucesso para {output_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao exportar dados para Excel: {e}")
            return False

    def get_all_records(self) -> List[Dict]:
        """
        Retorna todos os registros do banco de dados.
        
        Returns:
            Lista de dicionários contendo os registros.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM registros ORDER BY timestamp DESC")
                columns = [column[0] for column in cursor.description]
                records = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return records
        except Exception as e:
            logger.error(f"Erro ao obter registros: {e}")
            return []