import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple
import locale
import logging
from functools import lru_cache

# Configuração
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Definir manualmente os nomes dos meses como fallback
MESES_PT = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

class ValidadorNFE:
    def __init__(self, caminho_base: str):
        self.caminho_base = caminho_base
        self.colunas_necessarias = ["UF", "Nfe", "Pedido", "Planejamento"]
        self._configurar_locale()

    def _configurar_locale(self):
        """Configura o locale pt_BR com fallback para solução manual"""
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        except locale.Error:
            try:
                # Tentar variantes comuns do locale
                locale.setlocale(locale.LC_TIME, 'pt_BR')
                locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
                locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
            except locale.Error:
                logger.warning("Locale pt_BR não disponível, usando mapeamento manual de meses")
                self._usar_locale_manual = True
            else:
                self._usar_locale_manual = False
        else:
            self._usar_locale_manual = False

    def _parse_data(self, data_str: str) -> Tuple[int, int]:
        """Converte string de data para (ano, mês)"""
        formatos = [
            '%Y-%m-%d', '%d/%m/%Y', '%Y-%m', '%Y/%m',
            '%d-%m-%Y', '%m-%d-%Y', '%Y%m%d'
        ]
        
        for fmt in formatos:
            try:
                dt = datetime.strptime(data_str.strip(), fmt)
                return dt.year, dt.month
            except ValueError:
                continue
        return 0, 0

    def _parse_planejamento(self, planejamento: str) -> Tuple[int, int]:
        """Converte formato 'AAAA/mês' para (ano, mês)"""
        try:
            partes = planejamento.split('/')
            if len(partes) != 2:
                return 0, 0
                
            ano = int(partes[0])
            mes_str = partes[1].lower().strip()
            
            if self._usar_locale_manual:
                mes = MESES_PT.get(mes_str, 0)
            else:
                try:
                    # Tentar parsear usando o locale configurado
                    dt = datetime.strptime(mes_str, '%B')
                    mes = dt.month
                except ValueError:
                    mes = 0
            
            return ano, mes
        except (ValueError, AttributeError):
            return 0, 0

    @lru_cache(maxsize=1)
    def _carregar_base(self) -> pd.DataFrame:
        """Carrega e valida o arquivo base com cache"""
        try:
            df = pd.read_excel(self.caminho_base, engine='openpyxl')
            
            # Verifica colunas obrigatórias
            missing = [col for col in self.colunas_necessarias if col not in df.columns]
            if missing:
                raise ValueError(f"Colunas faltando na base: {missing}")

            # Limpeza de dados
            df = df[self.colunas_necessarias].copy()
            df = df.dropna()
            df['UF'] = df['UF'].astype(str).str.upper().str.strip()
            df['Nfe'] = pd.to_numeric(df['Nfe'], errors='coerce')
            df['Pedido'] = pd.to_numeric(df['Pedido'], errors='coerce')
            df = df.dropna()
            
            return df
        except Exception as e:
            logger.error(f"Erro ao carregar base: {str(e)}")
            raise

    def validar(self, uf: str, nfe: str, pedido: str, data_recebimento: str) -> Dict[str, Any]:
        """Executa toda a validação da nota fiscal"""
        resultado = {
            'uf': uf.upper() if uf else '',
            'nfe': nfe,
            'pedido': pedido,
            'data_recebimento': data_recebimento,
            'valido': False,
            'data_planejamento': '',
            'decisao': '',
            'mensagem': ''
        }

        try:
            # Validação básica
            if not all([uf, nfe, pedido, data_recebimento]):
                raise ValueError("Todos os campos são obrigatórios")

            # Conversão para tipos corretos
            try:
                nfe_int = int(nfe)
                pedido_int = int(pedido)
            except ValueError:
                raise ValueError("NFe e Pedido devem ser números válidos")

            # Carrega base de dados (usando cache)
            df = self._carregar_base()
            
            # Busca a nota fiscal
            registro = df[
                (df['UF'].str.upper() == uf.upper()) & 
                (df['Nfe'] == nfe_int) & 
                (df['Pedido'] == pedido_int)
            ]

            if registro.empty:
                raise ValueError("Nota fiscal não encontrada na base")

            # Processa datas
            planejamento = registro['Planejamento'].iloc[0]
            ano_plan, mes_plan = self._parse_planejamento(planejamento)
            ano_rec, mes_rec = self._parse_data(data_recebimento)

            if 0 in (ano_plan, mes_plan, ano_rec, mes_rec):
                raise ValueError("Formato de data inválido")

            # Toma decisão
            if (ano_plan < ano_rec) or (ano_plan == ano_rec and mes_plan <= mes_rec):
                decisao = "Pode abrir JIRA"
            else:
                decisao = "Abrir JIRA após o fechamento do mês"

            # Preenche resultado
            resultado.update({
                'valido': True,
                'data_planejamento': planejamento,
                'decisao': decisao,
                'mensagem': "Validação concluída com sucesso"
            })

        except Exception as e:
            resultado['mensagem'] = f"Erro na validação: {str(e)}"
            logger.error(f"Erro na validação: {str(e)}")

        return resultado