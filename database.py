import os
import base64
import json
from datetime import datetime
from typing import TypedDict, Optional, Dict, List, Any
import logging
import gspread
from google.oauth2.service_account import Credentials

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
    valido: bool
    data_planejamento: Optional[str]
    decisao: Optional[str]
    mensagem: Optional[str]

class DatabaseManager:
    def __init__(self, app=None):
        self.app = app
        self.gc = None
        self.spreadsheet = None
        self.worksheet = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Inicializa a conexão com Google Sheets"""
        try:
            # Obter credenciais da variável de ambiente
            creds_base64 = app.config.get("GOOGLE_CREDENTIALS_BASE64")
            if not creds_base64:
                raise ValueError("GOOGLE_CREDENTIALS_BASE64 não configurada")

            # Decodificar credenciais
            creds_json = base64.b64decode(creds_base64).decode('utf-8')
            creds_info = json.loads(creds_json)
            
            # Autenticar
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            self.gc = gspread.authorize(creds)
            
            # Acessar planilha
            spreadsheet_id = app.config.get("GOOGLE_SHEET_ID")
            if not spreadsheet_id:
                raise ValueError("GOOGLE_SHEET_ID não configurado")

            self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
            self.worksheet = self._get_or_create_worksheet("registros_nf")
            
            logger.info("Conexão com Google Sheets estabelecida com sucesso")
        except Exception as e:
            logger.critical(f"Falha na inicialização do Google Sheets: {str(e)}")
            raise

    def _get_or_create_worksheet(self, name: str):
        """Obtém ou cria a worksheet com cabeçalhos"""
        try:
            worksheet = self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title=name, rows=1000, cols=20)
            headers = [
                "id", "uf", "nfe", "pedido", "data_recebimento",
                "valido", "data_planejamento", "decisao", "mensagem",
                "criado_em", "atualizado_em"
            ]
            worksheet.append_row(headers)
            logger.info(f"Worksheet '{name}' criada com cabeçalhos")
        return worksheet

    def criar_registro(self, data: RegistroNF) -> Dict[str, Any]:
        """Cria um novo registro na planilha"""
        try:
            # Gerar ID sequencial
            next_id = len(self.worksheet.col_values(1))  # Conta linhas existentes
            
            registro = {
                "id": next_id,
                "uf": data["uf"].upper(),
                "nfe": int(data["nfe"]),
                "pedido": int(data["pedido"]),
                "data_recebimento": data["data_recebimento"],
                "valido": data.get("valido", True),
                "data_planejamento": data.get("data_planejamento", ""),
                "decisao": data.get("decisao", ""),
                "mensagem": data.get("mensagem", ""),
                "criado_em": datetime.now().isoformat(),
                "atualizado_em": datetime.now().isoformat()
            }
            
            self.worksheet.append_row(list(registro.values()))
            logger.info(f"Registro {next_id} adicionado com sucesso")
            return registro
            
        except Exception as e:
            logger.error(f"Erro ao criar registro: {str(e)}")
            raise

    def buscar_registro(self, uf: str, nfe: int) -> Optional[Dict]:
        """Busca um registro por UF e NFe"""
        try:
            records = self.worksheet.get_all_records()
            for record in records:
                if str(record["uf"]).upper() == uf.upper() and int(record["nfe"]) == nfe:
                    return record
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar registro: {str(e)}")
            return None

    def listar_registros(self) -> List[Dict]:
        """Lista todos os registros"""
        try:
            return self.worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Erro ao listar registros: {str(e)}")
            return []















