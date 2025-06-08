"""
Módulo de gerenciamento do banco de dados SQLite para o sistema de notas fiscais
Versão 2.0 - Com exportação robusta para Excel e tratamento completo de erros
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
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
        self._migrate_legacy_data()

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna uma conexão com o banco de dados."""
        return sqlite3.connect(self.db_path)

    def _initialize_db(self) -> None:
        """Cria a estrutura inicial do banco de dados."""
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
        """Migra dados do arquivo Excel legado para o SQLite."""
        legacy_path = Path('data/registros.xlsx')
        if not legacy_path.exists():
            return

        try:
            df = pd.read_excel(legacy_path, engine='openpyxl')
            
            # Verifica colunas obrigatórias
            required_cols = ['uf', 'nfe', 'pedido', 'data_recebimento']
            if not all(col in df.columns for col in required_cols):
                logger.error("Arquivo legado não contém colunas obrigatórias")
                return

            # Preenche valores padrão
            df['valido'] = df.get('valido', True)
            df['data_planejamento'] = df.get('data_planejamento', '')
            df['decisao'] = df.get('decisao', '')
            df['mensagem'] = df.get('mensagem', '')
            df['timestamp'] = df.get('timestamp', datetime.now())

            # Conversão segura de tipos
            df['nfe'] = pd.to_numeric(df['nfe'], errors='coerce').dropna().astype(int)
            df['pedido'] = pd.to_numeric(df['pedido'], errors='coerce').dropna().astype(int)
            
            # Remove linhas inválidas
            df = df.dropna(subset=required_cols)

            # Importa para o SQLite
            with self._get_connection() as conn:
                df.to_sql('registros', conn, if_exists='append', index=False)
                conn.commit()

            logger.info(f"Dados legados migrados: {len(df)} registros")
            legacy_path.rename(Path('data/registros_importados.xlsx'))

        except Exception as e:
            logger.error(f"Falha na migração de dados legados: {e}")

    def save_verification(self, data: Dict[str, Any]) -> bool:
        """
        Salva um registro de verificação no banco de dados.
        
        Args:
            data: Dicionário contendo:
                - uf (str)
                - nfe (int/str)
                - pedido (int/str)
                - data_recebimento (str)
                - valido (bool)
                - data_planejamento (str, optional)
                - decisao (str, optional)
                - mensagem (str, optional)
                - timestamp (str, optional)
                
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            # Validação dos campos obrigatórios
            required = ['uf', 'nfe', 'pedido', 'data_recebimento', 'valido']
            if not all(field in data for field in required):
                raise ValueError("Campos obrigatórios faltando")

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

    def export_to_excel(self, output_path: str) -> bool:
        """
        Exporta os registros para um arquivo Excel com tratamento robusto.
        
        Args:
            output_path: Caminho onde o arquivo será salvo
            
        Returns:
            bool: True se a exportação foi bem-sucedida
        """
        try:
            with self._get_connection() as conn:
                # Query com formatação segura de datas
                df = pd.read_sql("""
                    SELECT 
                        uf,
                        nfe,
                        pedido,
                        CASE 
                            WHEN date(data_recebimento) IS NULL THEN ''
                            ELSE strftime('%Y-%m-%d', data_recebimento)
                        END as data_recebimento,
                        valido,
                        data_planejamento,
                        decisao,
                        mensagem,
                        CASE 
                            WHEN datetime(timestamp) IS NULL THEN ''
                            ELSE strftime('%Y-%m-%d %H:%M:%S', timestamp)
                        END as timestamp
                    FROM registros
                    ORDER BY timestamp DESC
                """, conn)

                # Verifica se há dados para exportar
                if df.empty:
                    logger.warning("Nenhum dado encontrado para exportação")
                    return False

                # Conversão segura de tipos
                df['nfe'] = pd.to_numeric(df['nfe'], errors='coerce').fillna(0).astype(int)
                df['pedido'] = pd.to_numeric(df['pedido'], errors='coerce').fillna(0).astype(int)
                df['valido'] = df['valido'].apply(lambda x: 'Sim' if x else 'Não')

                # Ordem das colunas
                col_order = [
                    'uf', 'nfe', 'pedido', 'data_recebimento', 'valido',
                    'data_planejamento', 'decisao', 'mensagem', 'timestamp'
                ]
                df = df[col_order]

                # Exporta para Excel
                writer = pd.ExcelWriter(
                    output_path,
                    engine='openpyxl',
                    datetime_format='YYYY-MM-DD HH:MM:SS'
                )
                df.to_excel(
                    writer,
                    index=False,
                    sheet_name='Registros'
                )
                writer.close()
                return True

        except sqlite3.Error as e:
            logger.error(f"Erro no banco de dados durante exportação: {e}")
            return False
        except pd.errors.EmptyDataError:
            logger.error("Nenhum dado disponível para exportação")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado na exportação: {e}")
            return False

    def get_record_count(self) -> int:
        """Retorna o número total de registros válidos."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM registros")
            return cursor.fetchone()[0]

    def validate_data_integrity(self) -> Dict[str, Any]:
        """Verifica a integridade dos dados no banco."""
        results = {
            'total_registros': 0,
            'registros_invalidos': 0,
            'problemas': []
        }
        
        try:
            with self._get_connection() as conn:
                # Contagem total
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM registros")
                results['total_registros'] = cursor.fetchone()[0]

                # Verifica registros com problemas
                cursor.execute("""
                    SELECT id FROM registros 
                    WHERE nfe IS NULL 
                    OR pedido IS NULL 
                    OR date(data_recebimento) IS NULL
                """)
                invalid_records = cursor.fetchall()
                results['registros_invalidos'] = len(invalid_records)
                
                if invalid_records:
                    results['problemas'].append(
                        f"{len(invalid_records)} registros com dados inválidos"
                    )
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Erro na validação de dados: {e}")
            results['problemas'].append("Erro ao validar dados")
            return results

# Teste da classe
if __name__ == "__main__":
    # Configuração detalhada de logging para testes
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=== TESTE DO DATABASE MANAGER ===")
    
    # Cria instância
    db = DatabaseManager()
    
    # Teste de integridade
    print("\nVerificando integridade dos dados...")
    integrity = db.validate_data_integrity()
    print(f"Total de registros: {integrity['total_registros']}")
    print(f"Registros inválidos: {integrity['registros_invalidos']}")
    for problema in integrity['problemas']:
        print(f"Problema: {problema}")
    
    # Teste de exportação
    print("\nTestando exportação para Excel...")
    test_file = 'test_export.xlsx'
    
    if db.export_to_excel(test_file):
        print(f"✅ Exportação realizada com sucesso! Arquivo: {test_file}")
        
        # Verificação adicional do arquivo gerado
        try:
            test_df = pd.read_excel(test_file, engine='openpyxl')
            print(f"\nConteúdo do arquivo exportado:")
            print(f"- Total de registros: {len(test_df)}")
            print(f"- Colunas: {list(test_df.columns)}")
            print(f"- Primeira linha:\n{test_df.iloc[0]}")
        except Exception as e:
            print(f"❌ Erro ao verificar arquivo exportado: {e}")
    else:
        print("❌ Falha na exportação")
    
    print("\nTeste concluído!")