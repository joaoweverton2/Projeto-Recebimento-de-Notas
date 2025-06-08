"""
Módulo para gerenciamento do banco de dados SQLite do sistema de verificação de notas fiscais
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
        """
        Inicializa o gerenciador do banco de dados.
        
        Args:
            db_path: Caminho para o arquivo do banco de dados SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna uma conexão com o banco de dados."""
        return sqlite3.connect(self.db_path)

    def _initialize_db(self) -> None:
        """Cria a tabela se não existir."""
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

    def save_verification(self, data: Dict[str, Any]) -> bool:
        """
        Salva um registro de verificação no banco de dados.
        
        Args:
            data: Dicionário contendo os dados da verificação:
                - uf (str): Unidade Federativa
                - nfe (int/str): Número da NFe
                - pedido (int/str): Número do pedido
                - data_recebimento (str): Data de recebimento
                - valido (bool): Status da validação
                - data_planejamento (str, optional): Data de planejamento
                - decisao (str, optional): Decisão da validação
                - mensagem (str, optional): Mensagem adicional
                - timestamp (str, optional): Data/hora do registro
                
        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        try:
            # Verificação dos campos obrigatórios
            required = ['uf', 'nfe', 'pedido', 'data_recebimento', 'valido']
            if missing := [field for field in required if field not in data]:
                raise ValueError(f"Campos obrigatórios faltando: {missing}")

            # Prepara os valores
            values = (
                str(data['uf']),
                int(data['nfe']),
                int(data['pedido']),
                str(data['data_recebimento']),
                bool(data['valido']),
                str(data.get('data_planejamento', '')),
                str(data.get('decisao', '')),
                str(data.get('mensagem', '')),
                str(data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            )

            # Query SQL
            query = """
                INSERT INTO registros (
                    uf, nfe, pedido, data_recebimento, valido,
                    data_planejamento, decisao, mensagem, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Execução
            with self._get_connection() as conn:
                conn.execute(query, values)
                conn.commit()
                return True

        except sqlite3.Error as e:
            logger.error(f"Erro no banco de dados: {e}")
            return False
        except ValueError as e:
            logger.error(f"Erro de validação: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            return False

    def import_from_excel(self, excel_path: str) -> bool:
        """
        Importa dados de um arquivo Excel para o banco de dados.
        
        Args:
            excel_path: Caminho para o arquivo Excel
            
        Returns:
            bool: True se a importação foi bem-sucedida, False caso contrário
        """
        try:
            df = pd.read_excel(excel_path)
            
            # Verifica colunas obrigatórias
            required = ['uf', 'nfe', 'pedido', 'data_recebimento']
            if missing := [col for col in required if col not in df.columns]:
                raise ValueError(f"Colunas obrigatórias faltando: {missing}")

            # Preenche valores padrão
            df['valido'] = df.get('valido', True).astype(bool)
            df['timestamp'] = pd.to_datetime(df.get('timestamp', datetime.now())).dt.strftime('%Y-%m-%d %H:%M:%S')

            # Converte tipos
            df['nfe'] = df['nfe'].astype(int)
            df['pedido'] = df['pedido'].astype(int)

            with self._get_connection() as conn:
                df.to_sql('registros', conn, if_exists='append', index=False)
                conn.commit()
                logger.info(f"Importados {len(df)} registros do Excel")
                return True
                
        except Exception as e:
            logger.error(f"Erro na importação: {e}")
            return False

    def export_to_excel(self, output_path: str) -> bool:
        """
        Exporta os registros para um arquivo Excel.
        
        Args:
            output_path: Caminho onde o arquivo será salvo
            
        Returns:
            bool: True se a exportação foi bem-sucedida, False caso contrário
        """
        try:
            with self._get_connection() as conn:
                df = pd.read_sql("SELECT * FROM registros ORDER BY timestamp DESC", conn)
                
                # Converte booleanos para 0/1 para melhor compatibilidade com Excel
                if 'valido' in df.columns:
                    df['valido'] = df['valido'].astype(int)
                
                df.to_excel(output_path, index=False)
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Erro no banco de dados: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro na exportação: {e}")
            return False

    def get_record_count(self) -> int:
        """Retorna o número total de registros."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM registros")
            return cursor.fetchone()[0]

    def get_all_records(self) -> List[Dict]:
        """Retorna todos os registros."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM registros ORDER BY timestamp DESC")
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


# Teste da classe
if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Teste básico
    db = DatabaseManager()
    
    # Teste save_verification
    test_data = {
        'uf': 'SP',
        'nfe': '99999',
        'pedido': '88888',
        'data_recebimento': '2023-01-01',
        'valido': True
    }
    
    print("Testando save_verification...")
    if db.save_verification(test_data):
        print("✅ save_verification funcionando")
    else:
        print("❌ save_verification falhou")
    
    # Teste get_record_count
    print(f"\nTotal de registros: {db.get_record_count()}")
    
    # Teste export_to_excel
    print("\nTestando export_to_excel...")
    if db.export_to_excel('test_export.xlsx'):
        print("✅ export_to_excel funcionando")
    else:
        print("❌ export_to_excel falhou")