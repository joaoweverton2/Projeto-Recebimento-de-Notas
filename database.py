import os
from datetime import datetime
from typing import TypedDict, Optional, Dict, List, Any
import logging
import gspread
from google.oauth2.service_account import Credentials

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
    valido: Optional[bool]
    data_planejamento: Optional[str]
    decisao: Optional[str]
    mensagem: Optional[str]

class DatabaseManager:
    def __init__(self, app=None):
        self.gc = None
        self.worksheet = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Inicializa conexão com Google Sheets"""
        try:
            creds = Credentials.from_service_account_info(
                info=app.config["GOOGLE_CREDS_JSON"],
                scopes=SCOPES
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(
                app.config["GOOGLE_SHEET_ID"]
            ).worksheet("registros_nf")
            self._ensure_headers()
        except Exception as e:
            logger.error(f"Erro ao conectar: {str(e)}")
            raise

    def _ensure_headers(self):
        """Garante cabeçalhos mínimos"""
        headers = ["uf", "nfe", "pedido", "data_recebimento"]
        current = self.worksheet.row_values(1)
        if current != headers:
            self.worksheet.clear()
            self.worksheet.append_row(headers)

    def criar_registro(self, data: RegistroNF) -> bool:
        """Adiciona registro com campos essenciais"""
        try:
            row = [
                data["uf"].upper(),
                int(data["nfe"]),
                int(data["pedido"]),
                data["data_recebimento"],
                data.get("valido", True),
                data.get("data_planejamento", ""),
                data.get("decisao", ""),
                data.get("mensagem", "")
            ]
            self.worksheet.append_row(row)
            return True
        except Exception as e:
            logger.error(f"Erro ao criar registro: {str(e)}")
            return False

    def buscar_registro(self, uf: str, nfe: int) -> Optional[Dict]:
        """Busca por UF e NFe"""
        try:
            records = self.worksheet.get_all_records()
            for r in records:
                if r["uf"] == uf.upper() and int(r["nfe"]) == nfe:
                    return r
            return None
        except Exception as e:
            logger.error(f"Erro na busca: {str(e)}")
            return None















