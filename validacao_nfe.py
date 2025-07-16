"""
Módulo de Validação de Notas Fiscais - Versão 2.0
Correções aplicadas:
1. Validação robusta de todas as colunas de entrada
2. Suporte a múltiplos formatos de data
3. Integração correta com a base de notas
4. Mensagens de erro detalhadas
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple
import locale
import logging

# Configuração
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    pass

MESES = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

class ValidadorNFE:
    def __init__(self, caminho_base: str):
        self.caminho_base = caminho_base
        self.colunas_base = ["UF", "Nfe", "Pedido", "Planejamento"]
        self.colunas_registro = ["uf", "nfe", "pedido", "data_recebimento"]

    def _validar_formato_data(self, data_str: str) -> Tuple[int, int]:
        """Valida datas em múltiplos formatos (YYYY-MM-DD, DD/MM/YYYY, etc)"""
        formatos = [
            '%Y-%m-%d', '%d/%m/%Y', 
            '%Y-%m', '%Y/%m',
            '%d-%m-%Y', '%m-%d-%Y'
        ]
        
        for fmt in formatos:
            try:
                dt = datetime.strptime(data_str.strip(), fmt)
                return dt.year, dt.month
            except ValueError:
                continue
        return 0, 0

    def _validar_planejamento(self, planejamento: str) -> Tuple[int, int]:
        """Valida formato 'AAAA/mês' (ex: '2025/junho')"""
        try:
            ano, mes_str = planejamento.split('/')
            return int(ano), MESES.get(mes_str.lower().strip(), 0)
        except (ValueError, AttributeError):
            return 0, 0

    def _carregar_base_notas(self) -> pd.DataFrame:
        """Carrega e valida a base de notas fiscais"""
        try:
            df = pd.read_excel(self.caminho_base, engine='openpyxl')
            
            # Verifica colunas obrigatórias
            missing = [col for col in self.colunas_base if col not in df.columns]
            if missing:
                raise ValueError(f"Colunas faltando na base: {missing}")

            # Remove linhas inválidas
            df = df.dropna(subset=self.colunas_base)
            return df
        except Exception as e:
            logger.error(f"Falha ao carregar base: {str(e)}")
            raise

    def validar(self, uf: str, nfe: str, pedido: str, data_recebimento: str) -> Dict[str, Any]:
        """
        Validação completa com:
        - Verificação de campos obrigatórios
        - Consulta à base de notas
        - Decisão sobre abertura do JIRA
        """
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
            # Validação básica dos campos
            if not all([uf, nfe, pedido, data_recebimento]):
                raise ValueError("Todos os campos são obrigatórios")

            # Conversão para tipos corretos
            try:
                nfe_int = int(nfe)
                pedido_int = int(pedido)
            except ValueError:
                raise ValueError("NFe e Pedido devem ser números")

            # Carrega base de dados
            df = self._carregar_base_notas()
            
            # Busca a nota fiscal
            registro = df[
                (df['UF'].str.upper() == uf.upper()) & 
                (df['Nfe'] == nfe_int) & 
                (df['Pedido'] == pedido_int)
            ]

            if registro.empty:
                raise ValueError("Nota fiscal não encontrada")

            # Processa datas
            planejamento = registro['Planejamento'].iloc[0]
            ano_plan, mes_plan = self._validar_planejamento(planejamento)
            ano_rec, mes_rec = self._validar_formato_data(data_recebimento)

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

        return resultado