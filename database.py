import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

class DatabaseManager:
    def __init__(self, db_path: str = 'data/registros.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()
    
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
    
    def save_verification(self, data: dict) -> bool:
        """Salva um registro de verificação no banco de dados SQLite.
        
        Args:
            data: {
                'uf': str,               # Unidade Federativa
                'nfe': int/str,          # Número da NFe
                'pedido': int/str,       # Número do pedido
                'data_recebimento': str, # Data (YYYY-MM-DD)
                'valido': bool,          # Status da validação
                'data_planejamento': str, # Opcional
                'decisao': str,          # Opcional
                'mensagem': str,         # Opcional
                'timestamp': str         # Opcional
            }
        
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            # Verificação dos campos obrigatórios
            required = ['uf', 'nfe', 'pedido', 'data_recebimento', 'valido']
            if not all(field in data for field in required):
                raise ValueError(f"Campos obrigatórios faltando: {required}")
            
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
            
            # Executa a query
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO registros (
                        uf, nfe, pedido, data_recebimento, valido,
                        data_planejamento, decisao, mensagem, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, values)
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logging.error(f"Erro no banco de dados: {e}")
            return False
        except ValueError as e:
            logging.error(f"Dados inválidos: {e}")
            return False
        except Exception as e:
            logging.error(f"Erro inesperado: {e}")
            return False

# Teste da classe
if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(level=logging.INFO)
    
    # Cria instância
    db = DatabaseManager()
    
    # Dados de teste
    test_data = {
        'uf': 'SP',
        'nfe': '12345',
        'pedido': 67890,
        'data_recebimento': '2023-01-01',
        'valido': True
    }
    
    # Testa a função
    if db.save_verification(test_data):
        print("✅ Registro salvo com sucesso!")
    else:
        print("❌ Falha ao salvar registro")