import pandas as pd
from database import DatabaseManager
from main import app
import logging
from datetime import datetime
from typing import Dict, Any
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Migrador:
    def __init__(self, arquivo_origem: str):
        self.arquivo_origem = arquivo_origem
        self.colunas_necessarias = ["uf", "nfe", "pedido", "data_recebimento"]
        self._batch_size = 50  # Processar em lotes para evitar timeouts
        self._delay_between_batches = 5  # Segundos entre lotes

    def carregar_dados(self) -> pd.DataFrame:
        """Carrega e valida o arquivo de origem"""
        try:
            df = pd.read_excel(self.arquivo_origem, engine='openpyxl')
            
            # Verifica colunas
            missing = [col for col in self.colunas_necessarias if col not in df.columns]
            if missing:
                raise ValueError(f"Colunas faltando: {missing}")

            # Limpeza de dados
            df = df[self.colunas_necessarias].copy()
            df["uf"] = df["uf"].astype(str).str.upper().str.strip()
            df["nfe"] = pd.to_numeric(df["nfe"], errors="coerce")
            df["pedido"] = pd.to_numeric(df["pedido"], errors="coerce")
            df = df.dropna()
            
            # Converter datas para string no formato YYYY-MM-DD
            df["data_recebimento"] = pd.to_datetime(df["data_recebimento"]).dt.strftime('%Y-%m-%d')
            
            return df
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {str(e)}")
            raise

    def _processar_lote(self, db: DatabaseManager, lote: pd.DataFrame) -> Dict[str, int]:
        """Processa um lote de registros"""
        resultado_lote = {
            "sucesso": 0,
            "erros": 0
        }

        for _, row in lote.iterrows():
            try:
                registro = {
                    "uf": row["uf"],
                    "nfe": int(row["nfe"]),
                    "pedido": int(row["pedido"]),
                    "data_recebimento": row["data_recebimento"],
                    "valido": True,
                    "decisao": "Migrado",
                    "mensagem": "Migração inicial"
                }
                
                if db.criar_registro(registro):
                    resultado_lote["sucesso"] += 1
                else:
                    resultado_lote["erros"] += 1

                # Pequena pausa entre registros
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Erro no registro {row}: {str(e)}")
                resultado_lote["erros"] += 1

        return resultado_lote

    def migrar(self) -> Dict[str, Any]:
        """Executa a migração completa em lotes"""
        resultado = {
            "total": 0,
            "sucesso": 0,
            "erros": 0,
            "registros": []
        }

        with app.app_context():
            db = DatabaseManager(app)
            df = self.carregar_dados()
            resultado["total"] = len(df)

            # Processar em lotes
            for i in range(0, len(df), self._batch_size):
                lote = df.iloc[i:i + self._batch_size]
                logger.info(f"Processando lote {i//self._batch_size + 1}/{(len(df)-1)//self._batch_size + 1}")
                
                resultado_lote = self._processar_lote(db, lote)
                resultado["sucesso"] += resultado_lote["sucesso"]
                resultado["erros"] += resultado_lote["erros"]

                # Pausa entre lotes
                if i + self._batch_size < len(df):
                    time.sleep(self._delay_between_batches)

        return resultado

if __name__ == "__main__":
    try:
        migrador = Migrador("data/registros_antigos.xlsx")
        resultado = migrador.migrar()
        logger.info(f"Resultado final: {resultado['sucesso']}/{resultado['total']} migrados com sucesso")
        logger.info(f"Erros: {resultado['erros']}")
    except Exception as e:
        logger.error(f"Falha na migração: {str(e)}")
        raise