import pandas as pd
from database import DatabaseManager
from main import app
import logging
from datetime import datetime
from typing import Dict, Any
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Migrador:
    def __init__(self, app_instance):
        self.app = app_instance
        self.db = DatabaseManager(self.app)
        self._batch_size = 50  # Processar em lotes para evitar timeouts
        self._delay_between_batches = 5  # Segundos entre lotes

    def _carregar_excel_local(self, caminho_arquivo: str, colunas_necessarias: list) -> pd.DataFrame:
        """Carrega e valida um arquivo Excel local"""
        try:
            if not os.path.exists(caminho_arquivo):
                logger.warning(f"Arquivo local não encontrado: {caminho_arquivo}. Retornando DataFrame vazio.")
                return pd.DataFrame(columns=colunas_necessarias)

            df = pd.read_excel(caminho_arquivo, engine=\'openpyxl\')
            
            # Verifica colunas
            missing = [col for col in colunas_necessarias if col not in df.columns]
            if missing:
                raise ValueError(f"Colunas faltando em {caminho_arquivo}: {missing}")

            # Limpeza de dados
            df = df[colunas_necessarias].copy()
            df = df.dropna()
            
            return df
        except Exception as e:
            logger.error(f"Erro ao carregar dados do arquivo local {caminho_arquivo}: {str(e)}")
            raise

    def migrar_registros_antigos(self) -> Dict[str, Any]:
        """Migra registros de registros_antigos.xlsx para a planilha registros_nf"""
        logger.info("Iniciando migração de registros_antigos.xlsx para Google Sheets (registros_nf).")
        arquivo_origem = "data/registros_antigos.xlsx"
        colunas_necessarias = ["uf", "nfe", "pedido", "data_recebimento"]
        
        resultado = {
            "total": 0,
            "sucesso": 0,
            "erros": 0,
            "registros": []
        }

        try:
            df = self._carregar_excel_local(arquivo_origem, colunas_necessarias)
            resultado["total"] = len(df)

            for i in range(0, len(df), self._batch_size):
                lote = df.iloc[i:i + self._batch_size]
                logger.info(f"Processando lote {i//self._batch_size + 1}/{(len(df)-1)//self._batch_size + 1} de registros_antigos.")
                
                for _, row in lote.iterrows():
                    try:
                        registro = {
                            "uf": row["uf"].upper(),
                            "nfe": int(row["nfe"]),
                            "pedido": int(row["pedido"]),
                            "data_recebimento": pd.to_datetime(row["data_recebimento"]).strftime(\"%Y-%m-%d\"),
                            "data_planejamento": "", # Não existe em registros_antigos
                            "decisao": "Migrado",
                            "criado_em": datetime.now().isoformat()
                        }
                        self.db.criar_registro(registro)
                        resultado["sucesso"] += 1
                        time.sleep(0.1) # Pequena pausa entre registros
                    except Exception as e:
                        logger.error(f"Erro ao migrar registro {row.to_dict()}: {str(e)}")
                        resultado["erros"] += 1

                if i + self._batch_size < len(df):
                    time.sleep(self._delay_between_batches) # Pausa entre lotes
            logger.info(f"Migração de registros_antigos concluída: {resultado[\"sucesso\"]}/{resultado[\"total\"]} migrados com sucesso.")
        except Exception as e:
            logger.error(f"Falha geral na migração de registros_antigos: {str(e)}")
        return resultado

    def migrar_base_notas(self) -> Dict[str, Any]:
        """Migra Base_de_notas.xlsx para a planilha Base_de_notas no Google Sheets"""
        logger.info("Iniciando migração de Base_de_notas.xlsx para Google Sheets (Base_de_notas).")
        arquivo_origem = "data/Base_de_notas.xlsx"
        colunas_necessarias = ["UF", "Nfe", "Pedido", "Planejamento", "Demanda"]

        resultado = {
            "total": 0,
            "sucesso": 0,
            "erros": 0
        }

        try:
            df = self._carregar_excel_local(arquivo_origem, colunas_necessarias)
            resultado["total"] = len(df)
            
            if not df.empty:
                self.db.update_base_notas_data(df)
                resultado["sucesso"] = len(df)
                logger.info(f"Base_de_notas migrada com sucesso: {len(df)} registros.")
            else:
                logger.info("Base_de_notas.xlsx local vazia ou não encontrada, nenhuma migração necessária.")

        except Exception as e:
            logger.error(f"Falha na migração de Base_de_notas: {str(e)}")
            resultado["erros"] = resultado["total"]
        return resultado

if __name__ == "__main__":
    with app.app_context():
        migrador = Migrador(app)
        
        # Migrar registros_antigos.xlsx
        resultado_registros = migrador.migrar_registros_antigos()
        logger.info(f"Resultado final registros_antigos: {resultado_registros[\"sucesso\"]}/{resultado_registros[\"total\"]} migrados com sucesso. Erros: {resultado_registros[\"erros\"]}")

        # Migrar Base_de_notas.xlsx
        resultado_base_notas = migrador.migrar_base_notas()
        logger.info(f"Resultado final Base_de_notas: {resultado_base_notas[\"sucesso\"]}/{resultado_base_notas[\"total\"]} migrados com sucesso. Erros: {resultado_base_notas[\"erros\"]}")



