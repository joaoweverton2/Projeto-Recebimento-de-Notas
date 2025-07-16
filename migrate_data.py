import pandas as pd
from database import DatabaseManager
from main import app
import logging
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Migrador:
    def __init__(self, arquivo_origem: str):
        self.arquivo_origem = arquivo_origem
        self.colunas_necessarias = ["uf", "nfe", "pedido", "data_recebimento"]

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
            
            return df
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {str(e)}")
            raise

    def migrar(self) -> Dict[str, Any]:
        """Executa a migração completa"""
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

            for _, row in df.iterrows():
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
                        resultado["sucesso"] += 1
                        resultado["registros"].append(registro)
                    else:
                        resultado["erros"] += 1
                except Exception as e:
                    logger.error(f"Erro no registro {row}: {str(e)}")
                    resultado["erros"] += 1

        return resultado

if __name__ == "__main__":
    migrador = Migrador("data/registros_antigos.xlsx")
    resultado = migrador.migrar()
    logger.info(f"Resultado: {resultado['sucesso']}/{resultado['total']} migrados")