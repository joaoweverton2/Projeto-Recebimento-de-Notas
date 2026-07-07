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
        self._request_delay = 1.1
        self._falhas_consecutivas = 0
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
            
            # Worksheet da base de notas
            headers_base = ["UF", "Nfe", "Pedido", "Planejamento", "Demanda"]
            self.worksheet_base_notas = self._get_or_create_worksheet(self.NOME_PLANILHA_BASE, headers_base)
            
            logger.info(f"✅ Worksheets inicializadas: '{self.NOME_PLANILHA_REGISTROS}' e '{self.NOME_PLANILHA_BASE}'")
            
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

    def criar_registro(self, data: RegistroNF) -> Dict[str, Any]:
        """Cria um novo registro no SQLite e tenta sincronizar com Google Sheets"""
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
            
            # 1. Salva no SQLite (Persistência garantida)
            self.sqlite_manager.salvar_registro_sqlite(registro)
            logger.info(f"✅ Registro salvo no SQLite: {registro['uf']}/{registro['nfe']}")
            
            # 2. Tenta salvar no Google Sheets (Opcional/Backup)
            try:
                if self.worksheet_registros_nf:
                    row_data = [
                        registro["uf"], registro["nfe"], registro["pedido"],
                        registro["data_recebimento"], registro["data_planejamento"],
                        registro["decisao"], registro["criado_em"]
                    ]
                    self._rate_limit()
                    self.worksheet_registros_nf.append_row(row_data, value_input_option='USER_ENTERED')
                    logger.info(f"✅ Registro sincronizado com Google Sheets")
            except Exception as e:
                logger.warning(f"⚠️ Falha ao sincronizar com Google Sheets (registro mantido no SQLite): {e}")
            
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
        """Busca uma nota na Base_de_notas - primeiro SQLite, depois Google Sheets"""
        try:
            # Primeiro tenta SQLite (cache rápido)
            result = self.sqlite_manager.buscar_nota_sqlite(uf, nfe, pedido)
            if result:
                logger.debug(f"Nota encontrada no SQLite: {uf}/{nfe}/{pedido}")
                return result[0]
        except Exception as e:
            logger.warning(f"Erro no SQLite: {e}")
        
        # Se não encontrou, tenta Google Sheets e restaura cache
        try:
            logger.info(f"Nota não encontrada no SQLite, buscando no Google Sheets...")
            self._rate_limit()
            records = self.worksheet_base_notas.get_all_records()
            
            for record in records:
                if (str(record["UF"]).upper() == uf.upper() and 
                    int(record["Nfe"]) == nfe and 
                    int(record["Pedido"]) == pedido):
                    
                    # Restaura o cache completo
                    df_google = pd.DataFrame(records)
                    self.sqlite_manager.update_base_notas_data(df_google)
                    logger.info(f"✅ Cache do SQLite restaurado com {len(records)} registros")
                    return record
            
            return None
            
        except Exception as e:
            logger.error(f"Erro na busca do Google Sheets: {str(e)}")
            return None

    def listar_registros(self) -> List[Dict]:
        """Lista todos os registros - Prioriza SQLite para velocidade e confiabilidade"""
        try:
            registros = self.sqlite_manager.listar_registros_sqlite()
            if not registros:
                logger.info("SQLite sem registros, buscando no Google Sheets para restaurar...")
                try:
                    self._rate_limit()
                    registros_sheets = self.worksheet_registros_nf.get_all_records()
                    if registros_sheets:
                        for reg in registros_sheets:
                            # Ajusta tipos se necessário
                            reg_clean = {
                                "uf": str(reg.get("uf", "")),
                                "nfe": int(reg.get("nfe", 0)),
                                "pedido": int(reg.get("pedido", 0)),
                                "data_recebimento": str(reg.get("data_recebimento", "")),
                                "data_planejamento": str(reg.get("data_planejamento", "")),
                                "decisao": str(reg.get("decisao", "")),
                                "criado_em": str(reg.get("criado_em", ""))
                            }
                            self.sqlite_manager.salvar_registro_sqlite(reg_clean)
                        return self.sqlite_manager.listar_registros_sqlite()
                except Exception as e:
                    logger.error(f"Erro ao restaurar registros do Sheets: {e}")
            return registros
        except Exception as e:
            logger.error(f"Erro ao listar registros: {str(e)}")
            return []

    def get_base_notas_data(self) -> pd.DataFrame:
        """Obtém os dados da Base_de_notas - prioriza SQLite"""
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
        """Atualiza AMBOS os bancos: Google Sheets (primário) e SQLite (cache)"""
        if df.empty:
            logger.warning("DataFrame vazio - operação cancelada")
            return
        
        # 1. Atualiza Google Sheets (fonte primária)
        if self.worksheet_base_notas:
            try:
                self._rate_limit()
                # Limpa dados existentes
                self.worksheet_base_notas.clear()
                # Prepara dados: cabeçalhos + linhas
                dados = [df.columns.values.tolist()] + df.values.tolist()
                # Atualiza em lote
                self.worksheet_base_notas.update(dados, value_input_option='USER_ENTERED')
                logger.info(f"✅ '{self.NOME_PLANILHA_BASE}' atualizada no Google Sheets ({len(df)} registros)")
            except Exception as e:
                logger.error(f"Erro ao atualizar Google Sheets: {e}")
                raise
        
        # 2. Atualiza SQLite (cache)
        self.sqlite_manager.update_base_notas_data(df)
        logger.info(f"✅ Base_de_notas atualizada no SQLite ({len(df)} registros)")

    def verificar_saude_banco(self) -> Dict[str, Any]:
        """Verifica saúde dos bancos e consistência entre eles"""
        try:
            self._rate_limit()
            records_sheets = self.worksheet_base_notas.get_all_records()
            df_sheets = pd.DataFrame(records_sheets) if records_sheets else pd.DataFrame()
            df_sqlite = self.sqlite_manager.get_base_notas_data()
            
            sheets_count = len(df_sheets)
            sqlite_count = len(df_sqlite)
            
            return {
                'base_notas': {
                    'sheets_count': sheets_count,
                    'sqlite_count': sqlite_count,
                    'planilha_nome': self.NOME_PLANILHA_BASE,
                    'sincronizado': sheets_count == sqlite_count
                },
                'registros_nf': {
                    'planilha_nome': self.NOME_PLANILHA_REGISTROS
                },
                'status': 'OK' if sheets_count == sqlite_count else 'ATENÇÃO - Sincronização necessária'
            }
        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {e}")
            return {'erro': str(e), 'status': 'Erro'}

    def verificar_registros_nf(self) -> Dict[str, Any]:
        """Verifica o status da worksheet registros_nf com estatísticas detalhadas"""
        try:
            self._rate_limit()
            all_rows = self.worksheet_registros_nf.get_all_values()
            
            if not all_rows:
                return {
                    'existe': True,
                    'cabecalhos': [],
                    'total_registros': 0,
                    'ultimos_registros': [],
                    'estatisticas_decisoes': {},
                    'worksheet_name': self.NOME_PLANILHA_REGISTROS,
                    'status': 'Vazia'
                }
            
            headers = all_rows[0] if all_rows else []
            total_registros = len(all_rows) - 1 if len(all_rows) > 1 else 0
            
            # Últimos 10 registros
            ultimos_registros = []
            if len(all_rows) > 1:
                start_idx = max(1, len(all_rows) - 10)
                for row in all_rows[start_idx:]:
                    if len(row) >= 7:
                        ultimos_registros.append({
                            'uf': row[0] if row[0] else '',
                            'nfe': row[1] if row[1] else '',
                            'pedido': row[2] if row[2] else '',
                            'data_recebimento': row[3] if row[3] else '',
                            'data_planejamento': row[4] if row[4] else '',
                            'decisao': row[5] if row[5] else '',
                            'criado_em': row[6] if row[6] else ''
                        })
            
            # Estatísticas por decisão
            decisao_stats = {}
            if len(all_rows) > 1:
                for row in all_rows[1:]:
                    if len(row) >= 6:
                        decisao = row[5] if row[5] else 'Não registrada'
                        decisao_stats[decisao] = decisao_stats.get(decisao, 0) + 1
            
            return {
                'existe': True,
                'cabecalhos': headers,
                'total_registros': total_registros,
                'ultimos_registros': ultimos_registros,
                'estatisticas_decisoes': decisao_stats,
                'worksheet_name': self.NOME_PLANILHA_REGISTROS,
                'url_planilha': f"https://docs.google.com/spreadsheets/d/{self.spreadsheet.id}",
                'status': 'Operacional'
            }
            
        except gspread.WorksheetNotFound:
            logger.error(f"Worksheet '{self.NOME_PLANILHA_REGISTROS}' não encontrada")
            return {
                'existe': False,
                'erro': f'Worksheet "{self.NOME_PLANILHA_REGISTROS}" não encontrada',
                'status': 'Erro - Planilha não existe'
            }
        except Exception as e:
            logger.error(f"Erro ao verificar registros_nf: {e}")
            return {
                'existe': False,
                'erro': str(e),
                'status': 'Erro na verificação'
            }

    def forcar_sincronizacao(self) -> Dict[str, Any]:
        """Força a sincronização do Google Sheets para o SQLite"""
        logger.info("🔄 Forçando sincronização do Google Sheets para o SQLite...")
        try:
            self._rate_limit()
            records = self.worksheet_base_notas.get_all_records()
            
            if not records:
                logger.warning("Google Sheets está vazio. Nada para sincronizar.")
                return {
                    'success': False,
                    'message': 'Google Sheets está vazio',
                    'registros_sincronizados': 0
                }
            
            df_google = pd.DataFrame(records)
            self.sqlite_manager.update_base_notas_data(df_google)
            
            logger.info(f"✅ Sincronização concluída: {len(df_google)} registros")
            
            return {
                'success': True,
                'message': 'Sincronização realizada com sucesso',
                'registros_sincronizados': len(df_google),
                'sheets_count': len(df_google),
                'sqlite_count': len(self.sqlite_manager.get_base_notas_data())
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização forçada: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Falha na sincronização'
            }

    def limpar_cache_registros(self) -> Dict[str, Any]:
        """Limpa o cache do SQLite e recarrega do Google Sheets"""
        logger.info("🧹 Limpando cache do SQLite e recarregando do Google Sheets...")
        try:
            self._rate_limit()
            records = self.worksheet_base_notas.get_all_records()
            
            if not records:
                return {
                    'success': False,
                    'message': 'Google Sheets está vazio. Cache não pode ser restaurado.'
                }
            
            df_google = pd.DataFrame(records)
            self.sqlite_manager.update_base_notas_data(df_google)
            
            logger.info(f"✅ Cache limpo e recarregado com {len(df_google)} registros")
            
            return {
                'success': True,
                'message': f'Cache limpo e recarregado com {len(df_google)} registros do Google Sheets',
                'registros_carregados': len(df_google)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar cache: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Falha ao limpar cache'
            }