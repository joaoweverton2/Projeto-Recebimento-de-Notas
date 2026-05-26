import os
import base64
import json
from datetime import datetime
from typing import TypedDict, Optional, Dict, List, Any
import logging
import gspread
from google.oauth2.service_account import Credentials
import time
import pandas as pd
from database_sqlite import SQLiteManager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        self.sqlite_db_path = None
        self.sqlite_manager = None
        self._last_request_time = 0
        self._request_delay = 1.1
        self._falhas_consecutivas = 0
        # Nomes corretos das planilhas no Google Sheets
        self.NOME_PLANILHA_BASE = "Base_de_notas"
        self.NOME_PLANILHA_REGISTROS = "registros_nf"
        
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Inicializa a conexão com Google Sheets e SQLite"""
        try:
            # Configura SQLite
            self.sqlite_db_path = app.config.get("SQLITE_DB_PATH", "instance/data/base_notas.db")
            os.makedirs(os.path.dirname(self.sqlite_db_path), exist_ok=True)
            self.sqlite_manager = SQLiteManager(self.sqlite_db_path)
            
            # Configura Google Sheets
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
            
            # Inicializa as worksheets
            self._init_worksheets()
            
            # Sincroniza dados do Google Sheets para o SQLite na inicialização
            self._sincronizar_do_google_sheets()
            
            logger.info(f"✅ Conectado às planilhas: '{self.NOME_PLANILHA_REGISTROS}' e '{self.NOME_PLANILHA_BASE}'")
        except Exception as e:
            logger.critical(f"❌ Falha na inicialização: {str(e)}")
            raise

    def _init_worksheets(self):
        """Inicializa as worksheets com verificação rigorosa"""
        try:
            # Worksheet de registros (validações)
            headers_registros = ["uf", "nfe", "pedido", "data_recebimento", "data_planejamento", "decisao", "criado_em"]
            self.worksheet_registros_nf = self._get_or_create_worksheet(self.NOME_PLANILHA_REGISTROS, headers_registros)
            
            # Verifica cabeçalhos
            self._rate_limit()
            current_headers = self.worksheet_registros_nf.row_values(1)
            if not current_headers or current_headers != headers_registros:
                logger.warning("Cabeçalhos da worksheet registros_nf incorretos. Corrigindo...")
                self.worksheet_registros_nf.clear()
                self.worksheet_registros_nf.append_row(headers_registros)
                logger.info("✅ Cabeçalhos corrigidos")
            
            # Worksheet da base de notas - USANDO O NOME CORRETO "Base_de_notas"
            headers_base = ["UF", "Nfe", "Pedido", "Planejamento", "Demanda"]
            self.worksheet_base_notas = self._get_or_create_worksheet(self.NOME_PLANILHA_BASE, headers_base)
            
            logger.info(f"✅ Worksheets inicializadas: '{self.NOME_PLANILHA_REGISTROS}' e '{self.NOME_PLANILHA_BASE}'")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar worksheets: {e}")
            raise

    def _rate_limit(self):
        """Controla o rate limiting"""
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
            logger.debug(f"Worksheet '{name}' encontrada")
            return worksheet
            
        except gspread.WorksheetNotFound:
            self._rate_limit()
            worksheet = self.spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
            self._rate_limit()
            worksheet.append_row(headers)
            logger.info(f"✅ Worksheet '{name}' criada com cabeçalhos")
            return worksheet

    def _sincronizar_do_google_sheets(self):
        """Resgata dados do Google Sheets para o SQLite na inicialização"""
        try:
            df_local = self.sqlite_manager.get_base_notas_data()
            
            if df_local.empty:
                logger.info("SQLite vazio. Resgatando dados do Google Sheets...")
                
                if self.worksheet_base_notas:
                    self._rate_limit()
                    records = self.worksheet_base_notas.get_all_records()
                    if records:
                        df_google = pd.DataFrame(records)
                        self.sqlite_manager.update_base_notas_data(df_google)
                        logger.info(f"✅ Resgatados {len(df_google)} registros do Google Sheets")
                    else:
                        logger.info("Google Sheets também está vazio")
                else:
                    logger.warning(f"Worksheet '{self.NOME_PLANILHA_BASE}' não encontrada")
            else:
                logger.info(f"SQLite já possui {len(df_local)} registros")
                
        except Exception as e:
            logger.error(f"Erro ao sincronizar: {e}")

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
            
            if not self.worksheet_registros_nf:
                raise Exception("Worksheet registros_nf não disponível")
            
            row_data = list(registro.values())
            
            self._rate_limit()
            self.worksheet_registros_nf.append_row(row_data, value_input_option='USER_ENTERED')
            
            logger.info(f"✅ Registro salvo em '{self.NOME_PLANILHA_REGISTROS}': {registro['uf']}/{registro['nfe']}")
            return registro
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar registro: {str(e)}")
            raise

    def buscar_registro(self, uf: str, nfe: int) -> Optional[Dict]:
        """Busca um registro por UF e NFe"""
        try:
            self._rate_limit()
            records = self.worksheet_registros_nf.get_all_records()
            for record in records:
                if str(record["uf"]).upper() == uf.upper() and int(record["nfe"]) == nfe:
                    return record
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar registro: {str(e)}")
            return None

    def buscar_nota_base_notas(self, uf: str, nfe: int, pedido: int) -> Optional[Dict]:
        """Busca uma nota na Base_de_notas"""
        try:
            # Primeiro tenta SQLite
            result = self.sqlite_manager.buscar_nota_sqlite(uf, nfe, pedido)
            if result:
                return result[0]
        except Exception as e:
            logger.warning(f"Erro no SQLite: {e}")
        
        # Depois tenta Google Sheets
        try:
            logger.info(f"Buscando no Google Sheets...")
            self._rate_limit()
            records = self.worksheet_base_notas.get_all_records()
            
            for record in records:
                if (str(record["UF"]).upper() == uf.upper() and 
                    int(record["Nfe"]) == nfe and 
                    int(record["Pedido"]) == pedido):
                    
                    # Restaura cache
                    df_google = pd.DataFrame(records)
                    self.sqlite_manager.update_base_notas_data(df_google)
                    return record
            
            return None
            
        except Exception as e:
            logger.error(f"Erro na busca: {str(e)}")
            return None

    def listar_registros(self) -> List[Dict]:
        """Lista todos os registros"""
        try:
            self._rate_limit()
            return self.worksheet_registros_nf.get_all_records()
        except Exception as e:
            logger.error(f"Erro ao listar: {str(e)}")
            return []

    def get_base_notas_data(self) -> pd.DataFrame:
        """Obtém os dados da Base_de_notas"""
        df = self.sqlite_manager.get_base_notas_data()
        
        if df.empty and self.worksheet_base_notas:
            logger.warning("SQLite vazio, buscando do Google Sheets...")
            try:
                self._rate_limit()
                records = self.worksheet_base_notas.get_all_records()
                if records:
                    df = pd.DataFrame(records)
                    self.sqlite_manager.update_base_notas_data(df)
            except Exception as e:
                logger.error(f"Erro: {e}")
        
        return df

    def update_base_notas_data(self, df: pd.DataFrame):
        """Atualiza AMBOS os bancos"""
        if df.empty:
            logger.warning("DataFrame vazio")
            return
        
        # 1. Atualiza Google Sheets
        if self.worksheet_base_notas:
            try:
                self._rate_limit()
                self.worksheet_base_notas.clear()
                dados = [df.columns.values.tolist()] + df.values.tolist()
                self.worksheet_base_notas.update(dados, value_input_option='USER_ENTERED')
                logger.info(f"✅ '{self.NOME_PLANILHA_BASE}' atualizada ({len(df)} registros)")
            except Exception as e:
                logger.error(f"Erro no Sheets: {e}")
                raise
        
        # 2. Atualiza SQLite
        self.sqlite_manager.update_base_notas_data(df)

    def verificar_saude_banco(self) -> Dict[str, Any]:
        """Verifica saúde dos bancos"""
        try:
            self._rate_limit()
            records_sheets = self.worksheet_base_notas.get_all_records()
            df_sheets = pd.DataFrame(records_sheets) if records_sheets else pd.DataFrame()
            df_sqlite = self.sqlite_manager.get_base_notas_data()
            
            return {
                'base_notas': {
                    'sheets_count': len(df_sheets),
                    'sqlite_count': len(df_sqlite),
                    'planilha_nome': self.NOME_PLANILHA_BASE
                },
                'registros_nf': {
                    'planilha_nome': self.NOME_PLANILHA_REGISTROS
                },
                'status': 'OK'
            }
        except Exception as e:
            return {'erro': str(e), 'status': 'Erro'}