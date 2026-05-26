import os
import base64
import json
from datetime import datetime
from typing import TypedDict, Optional, Dict, List, Any
import logging
import gspread
from google.oauth2.service_account import Credentials
import time
from functools import lru_cache
import pandas as pd
from database_sqlite import SQLiteManager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class RegistroNF(TypedDict):
    uf: str
    nfe: int
    pedido: int
    data_recebimento: str
    data_planejamento: str
    decisao: str
    criado_em: str

class DatabaseManager:
    def __init__(self, app=None):
        self.app = app
        self.gc = None
        self.spreadsheet = None
        self.worksheet_registros_nf = None
        self.worksheet_base_notas = None
        self.sqlite_db_path = app.config.get("SQLITE_DB_PATH", "instance/data/base_notas.db")
        self.sqlite_manager = SQLiteManager(self.sqlite_db_path)
        self._last_request_time = 0
        self._request_delay = 1.1  # 1.1 segundos entre requisições
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Inicializa a conexão com Google Sheets"""
        try:
            creds_base64 = app.config.get("GOOGLE_CREDENTIALS_BASE64")
            if not creds_base64:
                raise ValueError("GOOGLE_CREDENTIALS_BASE64 não configurada")

            creds_json = base64.b64decode(creds_base64).decode('utf-8')
            creds_info = json.loads(creds_json)
            
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            self.gc = gspread.authorize(creds)
            
            spreadsheet_id = app.config.get("GOOGLE_SHEET_ID")
            if not spreadsheet_id:
                raise ValueError("GOOGLE_SHEET_ID não configurado")

            self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
            self.worksheet_registros_nf = self._get_or_create_worksheet("registros_nf", ["uf", "nfe", "pedido", "data_recebimento", "data_planejamento", "decisao", "criado_em"])
            # A Base_de_notas será gerenciada pelo SQLite
            logger.info("Conexão com Google Sheets estabelecida com sucesso")
        except Exception as e:
            logger.critical(f"Falha na inicialização do Google Sheets: {str(e)}")
            raise

    def _rate_limit(self):
        """Controla o rate limiting para evitar exceder quotas"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._request_delay:
            time.sleep(self._request_delay - elapsed)
        self._last_request_time = time.time()

    def _get_or_create_worksheet(self, name: str, headers: List[str]):
        """Obtém ou cria a worksheet com cabeçalhos"""
        try:
            self._rate_limit()
            worksheet = self.spreadsheet.worksheet(name)
            # Verifica se os cabeçalhos estão corretos, se não, adiciona
            if worksheet.row_values(1) != headers:
                worksheet.clear()
                worksheet.append_row(headers)
                logger.warning(f"Cabeçalhos da worksheet \'{name}\' corrigidos.")
        except gspread.WorksheetNotFound:
            self._rate_limit()
            worksheet = self.spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
            self._rate_limit()
            worksheet.append_row(headers)
            logger.info(f"Worksheet \'{name}\' criada com cabeçalhos.")
        return worksheet

    def criar_registro(self, data: RegistroNF) -> Dict[str, Any]:
        """Cria um novo registro na planilha registros_nf"""
        try:
            registro = {
                "uf": data["uf"].upper(),
                "nfe": int(data["nfe"]),
                "pedido": int(data["pedido"]),
                "data_recebimento": data["data_recebimento"],
                "data_planejamento": data.get("data_planejamento", ""),
                "decisao": data["decisao"],
                "criado_em": datetime.now().isoformat()
            }
            
            self._rate_limit()
            self.worksheet_registros_nf.append_row(list(registro.values()))
            logger.info("Registro adicionado com sucesso em registros_nf")
            return registro
            
        except Exception as e:
            logger.error(f"Erro ao criar registro em registros_nf: {str(e)}")
            raise

    def buscar_registro(self, uf: str, nfe: int) -> Optional[Dict]:
        """Busca um registro por UF e NFe em registros_nf (Google Sheets)"""
        try:
            self._rate_limit()
            records = self.worksheet_registros_nf.get_all_records()
            for record in records:
                if str(record["uf"]).upper() == uf.upper() and int(record["nfe"]) == nfe:
                    return record
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar registro em registros_nf (Google Sheets): {str(e)}")
            return None

    def buscar_nota_base_notas(self, uf: str, nfe: int, pedido: int) -> Optional[Dict]:
        """Busca uma nota por UF, NFe e Pedido na Base_de_notas (SQLite)"""
        try:
            result = self.sqlite_manager.buscar_nota_sqlite(uf, nfe, pedido)
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar nota na Base_de_notas (SQLite): {str(e)}")
            return None

    def listar_registros(self) -> List[Dict]:
        """Lista todos os registros de registros_nf"""
        try:
            self._rate_limit()
            return self.worksheet_registros_nf.get_all_records()
        except Exception as e:
            logger.error(f"Erro ao listar registros de registros_nf: {str(e)}")
            return []

    def get_base_notas_data(self) -> pd.DataFrame:
        """Obtém os dados da Base_de_notas do SQLite como DataFrame"""
        return self.sqlite_manager.get_base_notas_data()

    def update_base_notas_data(self, df: pd.DataFrame):
        """Atualiza a Base_de_notas no SQLite com um novo DataFrame"""
        self.sqlite_manager.update_base_notas_data(df)
        logger.info("Base_de_notas atualizada com sucesso no SQLite")


