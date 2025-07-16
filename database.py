import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, Any
import logging
import re

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database.log')
    ]
)
logger = logging.getLogger(__name__)

# Definição do escopo para acesso ao Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class RegistroNFInput(TypedDict):
    uf: str
    nfe: int
    pedido: int
    data_recebimento: str
    valido: Optional[bool]
    data_planejamento: Optional[str]
    decisao: Optional[str]
    mensagem: Optional[str]

class DatabaseManager:
    _MESES_PT = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }

    def __init__(self, app=None):
        self.app = app
        self.gc = None
        self.spreadsheet = None
        self.worksheet = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        self.app = app
        self._initialize_google_sheets()

    def _initialize_google_sheets(self) -> None:
        logger.info("Iniciando _initialize_google_sheets...")
        try:
            import base64
            import json

            creds_base64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
            if not creds_base64:
                logger.error("Variável de ambiente GOOGLE_CREDENTIALS_BASE64 não configurada.")
                raise ValueError("GOOGLE_CREDENTIALS_BASE64 não configurado.")
            logger.info("GOOGLE_CREDENTIALS_BASE64 encontrada.")

            creds_json = base64.b64decode(creds_base64).decode("utf-8")
            logger.info("Credenciais Base64 decodificadas para JSON.")
            creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
            logger.info("Credenciais de serviço carregadas.")
            
            self.gc = gspread.authorize(creds)            
            logger.info("gspread autorizado.")

            spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
            if not spreadsheet_id:
                logger.error("Variável de ambiente GOOGLE_SHEET_ID não configurada.")
                raise ValueError("GOOGLE_SHEET_ID não configurado.")
            logger.info(f"GOOGLE_SHEET_ID encontrada: {spreadsheet_id}")

            self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
            logger.info(f"Planilha aberta: {self.spreadsheet.title}")
            self.worksheet = self.spreadsheet.worksheet("registros_nf") # Nome da aba da planilha
            logger.info("Conexão com Google Sheets estabelecida com sucesso na aba 'registros_nf'.")
            
            # Garante que o cabeçalho exista
            self._ensure_headers()

        except Exception as e:
            logger.error(f"Falha ao inicializar Google Sheets: {str(e)}")
            raise

    def _ensure_headers(self):
        headers = ["id", "uf", "nfe", "pedido", "data_recebimento", "valido", 
                   "data_planejamento", "decisao", "mensagem", "criado_em", "atualizado_em"]
        logger.info("Verificando cabeçalhos da planilha...")
        try:
            current_headers = self.worksheet.row_values(1)
            if current_headers != headers:
                if not current_headers:
                    self.worksheet.append_row(headers)
                    logger.info("Cabeçalhos adicionados à planilha.")
                else:
                    logger.warning("Cabeçalhos da planilha não correspondem ao esperado. Por favor, verifique a planilha.")
            else:
                logger.info("Cabeçalhos da planilha estão corretos.")
        except Exception as e:
            logger.error(f"Erro ao verificar/adicionar cabeçalhos: {str(e)}")
            raise

    def _parse_date(self, date_str: str) -> datetime.date:
        if not date_str or not isinstance(date_str, str):
            return datetime.now().date()
            
        date_str = date_str.strip().lower()
        
        if 't' in date_str:
            date_str = date_str.split('t')[0]
        
        if ' ' in date_str and ':' in date_str:
            date_str = date_str.split(' ')[0]
        
        mes_pt_match = re.match(r'(\d{4})[/-]([a-zç]+)' , date_str)
        if mes_pt_match:
            ano = int(mes_pt_match.group(1))
            mes_nome = mes_pt_match.group(2)
            if mes_nome in self._MESES_PT:
                return datetime(ano, self._MESES_PT[mes_nome], 1).date()
        
        formats_to_try = [
            '%Y-%m-%d', 
            '%Y/%m/%d', 
            '%Y-%m', 
            '%Y/%m', 
            '%d/%m/%Y', 
            '%m/%d/%Y',
        ]
        
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_str, fmt)
                if fmt in ['%Y-%m', '%Y/%m']:
                    return dt.date().replace(day=1)
                return dt.date()
            except ValueError:
                continue
        
        logger.warning(f"Formato de data não reconhecido: {date_str}. Usando data atual.")
        return datetime.now().date()

    def _get_next_id(self) -> int:
        logger.info("Obtendo próximo ID...")
        try:
            all_ids = self.worksheet.col_values(1)[1:] # Ignora o cabeçalho
            if not all_ids:
                logger.info("Nenhum ID existente, retornando 1.")
                return 1
            next_id = max([int(i) for i in all_ids if i.isdigit()]) + 1
            logger.info(f"Próximo ID: {next_id}")
            return next_id
        except Exception as e:
            logger.error(f"Erro ao obter próximo ID: {str(e)}")
            return 1

    def criar_registro(self, data: RegistroNFInput) -> Optional[Dict[str, Any]]:
        logger.info(f"Tentando criar registro para UF={data['uf']}, NFe={data['nfe']}")
        try:
            existing = self.obter_registro_por_nfe(data['uf'], data['nfe'])
            if existing:
                logger.warning(f"Registro já existe: {data['uf']}-{data['nfe']}")
                return existing
            
            next_id = self._get_next_id()
            
            data_recebimento_obj = self._parse_date(data['data_recebimento'])
            data_planejamento_obj = self._parse_date(data['data_planejamento']) if data.get('data_planejamento') else None

            row = [
                next_id,
                data['uf'].upper()[:6],
                data['nfe'],
                data['pedido'],
                data_recebimento_obj.isoformat(),
                data.get('valido', True),
                data_planejamento_obj.isoformat() if data_planejamento_obj else '',
                data.get('decisao', ''),
                data.get('mensagem', ''),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ]
            logger.info(f"Dados do registro a serem adicionados: {row}")
            self.worksheet.append_row(row)
            logger.info(f"Registro criado e adicionado à planilha: {row}")
            return self._row_to_dict(row)
        except Exception as e:
            logger.error(f"Falha ao criar registro: {str(e)}")
            return None

    def obter_registro(self, registro_id: int) -> Optional[Dict[str, Any]]:
        logger.info(f"Obtendo registro por ID: {registro_id}")
        try:
            records = self.worksheet.get_all_records()
            for record in records:
                if record.get('id') == registro_id:
                    logger.info(f"Registro encontrado: {record}")
                    return record
            logger.info(f"Registro com ID {registro_id} não encontrado.")
            return None
        except Exception as e:
            logger.error(f"Falha ao obter registro por ID: {str(e)}")
            return None

    def obter_registro_por_nfe(self, uf: str, nfe: int) -> Optional[Dict[str, Any]]:
        logger.info(f"Obtendo registro por UF={uf}, NFe={nfe}")
        try:
            records = self.worksheet.get_all_records()
            for record in records:
                if str(record.get('uf', '')).upper() == uf.upper() and int(record.get('nfe', 0)) == nfe:
                    logger.info(f"Registro encontrado: {record}")
                    return record
            logger.info(f"Registro com UF={uf}, NFe={nfe} não encontrado.")
            return None
        except Exception as e:
            logger.error(f"Falha ao obter registro por NFE: {str(e)}")
            return None

    def atualizar_registro(self, registro_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        logger.info(f"Atualizando registro ID: {registro_id} com dados: {data}")
        try:
            all_values = self.worksheet.get_all_values()
            headers = all_values[0]
            records = all_values[1:]

            row_index = -1
            for i, row in enumerate(records):
                if row and row[0] and int(row[0]) == registro_id:
                    row_index = i + 2 # +2 porque get_all_values é 0-indexed e headers são 1 linha
                    break
            
            if row_index == -1:
                logger.warning(f"Registro com ID {registro_id} não encontrado para atualização.")
                return None

            current_row_data = records[row_index - 2] # -2 para pegar a linha correta no records
            updated_row = list(current_row_data) # Converte para lista mutável

            for key, value in data.items():
                if key in headers:
                    col_index = headers.index(key)
                    if key == 'data_recebimento' or key == 'data_planejamento':
                        parsed_date = self._parse_date(value) if value else None
                        updated_row[col_index] = parsed_date.isoformat() if parsed_date else ''
                    elif key == 'valido':
                        updated_row[col_index] = bool(value)
                    else:
                        updated_row[col_index] = value
            
            # Atualiza a coluna atualizado_em
            if 'atualizado_em' in headers:
                updated_row[headers.index('atualizado_em')] = datetime.utcnow().isoformat()

            self.worksheet.update(f'A{row_index}:K{row_index}' , [updated_row])
            logger.info(f"Registro atualizado: ID {registro_id}")
            return self._row_to_dict(updated_row)
        except Exception as e:
            logger.error(f"Falha ao atualizar registro {registro_id}: {str(e)}")
            return None

    def remover_registro(self, registro_id: int) -> bool:
        logger.info(f"Removendo registro ID: {registro_id}")
        try:
            all_values = self.worksheet.get_all_values()
            records = all_values[1:]

            row_index = -1
            for i, row in enumerate(records):
                if row and row[0] and int(row[0]) == registro_id:
                    row_index = i + 2 # +2 porque get_all_values é 0-indexed e headers são 1 linha
                    break
            
            if row_index == -1:
                logger.warning(f"Registro com ID {registro_id} não encontrado para remoção.")
                return False

            self.worksheet.delete_rows(row_index)
            logger.info(f"Registro removido: ID {registro_id}")
            return True
        except Exception as e:
            logger.error(f"Falha ao remover registro {registro_id}: {str(e)}")
            return False

    def listar_registros(self, filtros: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        logger.info(f"Listando registros com filtros: {filtros}, limite: {limit}")
        try:
            records = self.worksheet.get_all_records()
            
            filtered_records = []
            for record in records:
                match = True
                if filtros:
                    for key, value in filtros.items():
                        if key in record and record[key] != value:
                            match = False
                            break
                if match:
                    filtered_records.append(record)
            
            if limit:
                filtered_records = filtered_records[:limit]
            logger.info(f"Retornando {len(filtered_records)} registros filtrados.")
            return filtered_records
        except Exception as e:
            logger.error(f"Falha ao listar registros: {str(e)}")
            return []

    def exportar_para_excel(self, filepath: str) -> bool:
        logger.info(f"Exportando dados para Excel: {filepath}")
        try:
            records = self.worksheet.get_all_records()
            df = pd.DataFrame(records)
            df.to_excel(filepath, index=False, engine='openpyxl')
            logger.info(f"Dados exportados para {filepath}")
            return True
        except Exception as e:
            logger.error(f"Falha ao exportar dados para Excel: {str(e)}")
            return False

    def remover_registros_teste(self) -> int:
        logger.info("Removendo registros de teste...")
        try:
            all_values = self.worksheet.get_all_values()
            headers = all_values[0]
            records = all_values[1:]
            
            rows_to_delete = []
            for i, row in enumerate(records):
                record_dict = dict(zip(headers, row))
                if (record_dict.get('nfe') == 999999 or record_dict.get('pedido') == 999999):
                    rows_to_delete.append(i + 2) # +2 para ajustar o índice da planilha
            
            if not rows_to_delete:
                logger.info("Nenhum registro de teste encontrado para remoção.")
                return 0

            # Deletar linhas em ordem reversa para não afetar os índices
            deleted_count = 0
            for row_idx in sorted(rows_to_delete, reverse=True):
                self.worksheet.delete_rows(row_idx)
                deleted_count += 1
            
            logger.info(f"Removidos {deleted_count} registros de teste.")
            return deleted_count
        except Exception as e:
            logger.error(f"Falha ao remover registros de teste: {str(e)}")
            return 0

    def _row_to_dict(self, row_values: List[Any]) -> Dict[str, Any]:
        headers = ["id", "uf", "nfe", "pedido", "data_recebimento", "valido", 
                   "data_planejamento", "decisao", "mensagem", "criado_em", "atualizado_em"]
        return dict(zip(headers, row_values))

# Testes (removidos para evitar execução direta e conflito com Flask app)
# if __name__ == "__main__":
#    print("Este módulo não deve ser executado diretamente. Use o Flask app.")













