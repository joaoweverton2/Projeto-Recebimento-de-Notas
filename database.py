import os
import base64
import json
from datetime import datetime
from typing import TypedDict, Optional, Dict, List, Any
import logging
import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import GoogleAuthError
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
        self._request_delay = 1.1  # 1.1 segundos entre requisições
        self._falhas_consecutivas = 0
        
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Inicializa a conexão com Google Sheets e SQLite"""
        try:
            # Configura SQLite
            self.sqlite_db_path = app.config.get("SQLITE_DB_PATH", "instance/data/base_notas.db")
            # Garante que o diretório exista
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
            
            logger.info("✅ Conexão com Google Sheets estabelecida e SQLite sincronizado")
        except Exception as e:
            logger.critical(f"❌ Falha na inicialização: {str(e)}")
            raise

    def _init_worksheets(self):
        """Inicializa as worksheets com verificação rigorosa"""
        try:
            # Worksheet de registros (validações)
            headers_registros = ["uf", "nfe", "pedido", "data_recebimento", "data_planejamento", "decisao", "criado_em"]
            self.worksheet_registros_nf = self._get_or_create_worksheet("registros_nf", headers_registros)
            
            # Verifica se a worksheet está acessível e com cabeçalhos corretos
            self._rate_limit()
            current_headers = self.worksheet_registros_nf.row_values(1)
            if not current_headers or current_headers != headers_registros:
                logger.warning("Cabeçalhos da worksheet registros_nf incorretos. Corrigindo...")
                self.worksheet_registros_nf.clear()
                self.worksheet_registros_nf.append_row(headers_registros)
                logger.info("✅ Cabeçalhos da worksheet registros_nf corrigidos")
            
            # Worksheet da base de notas
            headers_base = ["UF", "Nfe", "Pedido", "Planejamento", "Demanda"]
            self.worksheet_base_notas = self._get_or_create_worksheet("base_notas", headers_base)
            
            logger.info("✅ Worksheets inicializadas com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar worksheets: {e}")
            raise

    def _rate_limit(self):
        """Controla o rate limiting para evitar exceder quotas do Google Sheets API"""
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
            return worksheet
            
        except gspread.WorksheetNotFound:
            self._rate_limit()
            worksheet = self.spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
            self._rate_limit()
            worksheet.append_row(headers)
            logger.info(f"✅ Worksheet '{name}' criada com cabeçalhos.")
            return worksheet

    def _sincronizar_do_google_sheets(self):
        """Resgata dados do Google Sheets para o SQLite na inicialização"""
        try:
            # Verifica se o SQLite está vazio
            df_local = self.sqlite_manager.get_base_notas_data()
            
            if df_local.empty:
                logger.info("SQLite vazio. Tentando resgatar dados do Google Sheets...")
                
                # Busca dados do Google Sheets
                if self.worksheet_base_notas:
                    self._rate_limit()
                    records = self.worksheet_base_notas.get_all_records()
                    if records:
                        df_google = pd.DataFrame(records)
                        # Salva no SQLite
                        self.sqlite_manager.update_base_notas_data(df_google)
                        logger.info(f"✅ Resgatados {len(df_google)} registros do Google Sheets para SQLite")
                    else:
                        logger.info("Google Sheets também está vazio. Banco de dados iniciado do zero.")
                else:
                    logger.warning("Worksheet Base_de_notas não encontrada no Google Sheets")
            else:
                logger.info(f"SQLite já possui {len(df_local)} registros. Sincronização não necessária.")
                
        except Exception as e:
            logger.error(f"Erro ao sincronizar do Google Sheets: {e}")

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
            
            # Verifica se a worksheet existe e está acessível
            if not self.worksheet_registros_nf:
                logger.error("Worksheet registros_nf não inicializada")
                raise Exception("Worksheet registros_nf não disponível")
            
            # Prepara a linha para adicionar
            row_data = [
                registro["uf"],
                registro["nfe"],
                registro["pedido"],
                registro["data_recebimento"],
                registro["data_planejamento"],
                registro["decisao"],
                registro["criado_em"]
            ]
            
            # Adiciona o registro com retry automático
            max_retries = 3
            for tentativa in range(max_retries):
                try:
                    self._rate_limit()
                    self.worksheet_registros_nf.append_row(row_data, value_input_option='USER_ENTERED')
                    
                    logger.info(f"✅ Registro ADICIONADO ao Google Sheets: UF={registro['uf']}, NFe={registro['nfe']}, Decisão={registro['decisao']}")
                    self._falhas_consecutivas = 0
                    break
                    
                except gspread.exceptions.APIError as e:
                    if tentativa < max_retries - 1:
                        logger.warning(f"Tentativa {tentativa + 1} falhou. Reconnectando...")
                        time.sleep(2 ** tentativa)  # Exponential backoff
                        self._reconectar_google_sheets()
                    else:
                        raise e
            
            return registro
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar registro: {str(e)}")
            self._falhas_consecutivas += 1
            raise

    def _reconectar_google_sheets(self):
        """Tenta reconectar ao Google Sheets em caso de erro"""
        try:
            logger.info("Tentando reconectar ao Google Sheets...")
            creds_base64 = self.app.config.get("GOOGLE_CREDENTIALS_BASE64")
            creds_json = base64.b64decode(creds_base64).decode('utf-8')
            creds_info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            self.gc = gspread.authorize(creds)
            spreadsheet_id = self.app.config.get("GOOGLE_SHEET_ID")
            self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
            self._init_worksheets()
            logger.info("✅ Reconectado ao Google Sheets com sucesso")
        except Exception as e:
            logger.error(f"❌ Falha na reconexão: {e}")

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
            logger.error(f"Erro ao buscar registro: {str(e)}")
            return None

    def buscar_nota_base_notas(self, uf: str, nfe: int, pedido: int) -> Optional[Dict]:
        """Busca uma nota por UF, NFe e Pedido na Base_de_notas"""
        try:
            # Primeiro tenta no SQLite (cache)
            result = self.sqlite_manager.buscar_nota_sqlite(uf, nfe, pedido)
            if result:
                logger.debug(f"Nota encontrada no SQLite: {uf}/{nfe}/{pedido}")
                return result[0]
        except Exception as e:
            logger.warning(f"Erro ao buscar no SQLite: {e}")
        
        # Se não encontrou no SQLite, tenta no Google Sheets
        try:
            logger.info(f"Nota não encontrada no SQLite, buscando no Google Sheets...")
            self._rate_limit()
            records = self.worksheet_base_notas.get_all_records()
            
            for record in records:
                if (str(record["UF"]).upper() == uf.upper() and 
                    int(record["Nfe"]) == nfe and 
                    int(record["Pedido"]) == pedido):
                    
                    # Restaura cache
                    df_google = pd.DataFrame(records)
                    self.sqlite_manager.update_base_notas_data(df_google)
                    logger.info(f"✅ Cache do SQLite restaurado com {len(records)} registros")
                    return record
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar nota no Google Sheets: {str(e)}")
            return None

    def listar_registros(self) -> List[Dict]:
        """Lista todos os registros de registros_nf"""
        try:
            self._rate_limit()
            return self.worksheet_registros_nf.get_all_records()
        except Exception as e:
            logger.error(f"Erro ao listar registros: {str(e)}")
            return []

    def get_base_notas_data(self) -> pd.DataFrame:
        """Obtém os dados da Base_de_notas"""
        df = self.sqlite_manager.get_base_notas_data()
        
        if df.empty and self.worksheet_base_notas:
            logger.warning("SQLite vazio, buscando dados do Google Sheets...")
            try:
                self._rate_limit()
                records = self.worksheet_base_notas.get_all_records()
                if records:
                    df = pd.DataFrame(records)
                    self.sqlite_manager.update_base_notas_data(df)
                    logger.info(f"✅ Restaurados {len(df)} registros do Google Sheets")
            except Exception as e:
                logger.error(f"Erro ao buscar dados do Google Sheets: {e}")
        
        return df

    def update_base_notas_data(self, df: pd.DataFrame):
        """Atualiza AMBOS: Google Sheets e SQLite"""
        if df.empty:
            logger.warning("Tentativa de atualizar com DataFrame vazio")
            return
        
        # 1. Atualiza Google Sheets
        if self.worksheet_base_notas:
            try:
                self._rate_limit()
                # Limpa dados existentes
                self.worksheet_base_notas.clear()
                # Prepara dados
                dados = [df.columns.values.tolist()] + df.values.tolist()
                # Atualiza
                self.worksheet_base_notas.update(dados, value_input_option='USER_ENTERED')
                logger.info(f"✅ Base_de_notas atualizada no Google Sheets ({len(df)} registros)")
            except Exception as e:
                logger.error(f"Erro ao atualizar Google Sheets: {e}")
                raise
        
        # 2. Atualiza SQLite
        self.sqlite_manager.update_base_notas_data(df)
        logger.info(f"✅ Base_de_notas atualizada no SQLite ({len(df)} registros)")

    def verificar_registros_nf(self) -> Dict[str, Any]:
        """Verifica o status da worksheet registros_nf"""
        try:
            self._rate_limit()
            # Pega todas as linhas
            all_rows = self.worksheet_registros_nf.get_all_values()
            
            # Pega os cabeçalhos
            headers = all_rows[0] if all_rows else []
            
            # Conta registros (excluindo cabeçalho)
            total_registros = len(all_rows) - 1 if len(all_rows) > 1 else 0
            
            # Últimos 5 registros
            ultimos_registros = []
            if len(all_rows) > 1:
                for row in all_rows[-5:]:
                    if len(row) >= 7:
                        ultimos_registros.append({
                            'uf': row[0],
                            'nfe': row[1],
                            'pedido': row[2],
                            'decisao': row[5],
                            'data': row[6]
                        })
            
            return {
                'existe': True,
                'cabecalhos': headers,
                'total_registros': total_registros,
                'ultimos_registros': ultimos_registros,
                'worksheet_name': self.worksheet_registros_nf.title
            }
        except Exception as e:
            logger.error(f"Erro ao verificar registros_nf: {e}")
            return {'existe': False, 'erro': str(e)}

    def verificar_saude_banco(self) -> Dict[str, Any]:
        """Verifica consistência entre Google Sheets e SQLite"""
        try:
            # Verifica registros_nf
            registros_status = self.verificar_registros_nf()
            
            # Dados do Google Sheets
            self._rate_limit()
            records_sheets = self.worksheet_base_notas.get_all_records()
            df_sheets = pd.DataFrame(records_sheets) if records_sheets else pd.DataFrame()
            
            # Dados do SQLite
            df_sqlite = self.sqlite_manager.get_base_notas_data()
            
            return {
                'base_notas': {
                    'sheets_count': len(df_sheets),
                    'sqlite_count': len(df_sqlite),
                    'sincronizado': len(df_sheets) == len(df_sqlite) if len(df_sheets) > 0 else True
                },
                'registros_nf': registros_status,
                'status': 'Operacional'
            }
        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {e}")
            return {'erro': str(e), 'status': 'Erro'}

    def forcar_sincronizacao(self):
        """Força sincronização do Google Sheets para o SQLite"""
        logger.info("Forçando sincronização...")
        self._sincronizar_do_google_sheets()
        return self.verificar_saude_banco()