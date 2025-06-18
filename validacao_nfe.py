"""
Módulo de validação de Notas Fiscais

Este módulo contém as funções necessárias para validar notas fiscais contra uma base de dados
e determinar se um JIRA deve ser aberto imediatamente ou após o fechamento do mês.
"""

import pandas as pd
import os
from datetime import datetime
import locale
from typing import Dict, Tuple, List, Optional, Any
import pytz  # Adicione no início do arquivo

# Configurar locale para português brasileiro
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
    except:
        pass  # Se não conseguir configurar o locale, usaremos uma abordagem alternativa
# Mapeamento de nomes de meses em português para números
MESES = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
    'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

def carregar_base_dados(caminho_arquivo: str) -> pd.DataFrame:
    """
    Carrega a base de dados de notas fiscais a partir de um arquivo Excel.
    Sempre recarrega o arquivo para garantir dados atualizados.
    
    Args:
        caminho_arquivo: Caminho para o arquivo Excel contendo a base de dados.
        
    Returns:
        DataFrame contendo os dados das notas fiscais.
    """
    try:
        # Força o recarregamento do arquivo a cada chamada
        # Isso garante que mudanças no arquivo sejam refletidas imediatamente
        print(f"🔄 Carregando base de dados: {caminho_arquivo}")
        df = pd.read_excel(caminho_arquivo, engine='openpyxl')
        print(f"📊 Base carregada com {len(df)} registros")
        return df
    except Exception as e:
        print(f"❌ Erro ao carregar a base de dados: {e}")
        return pd.DataFrame()

def extrair_mes_ano_planejamento(data_planejamento: str) -> Tuple[int, int]:
    """
    Extrai o mês e o ano da data de planejamento no formato 'AAAA/mês'.
    
    Args:
        data_planejamento: String no formato 'AAAA/mês' (ex: '2025/maio').
        
    Returns:
        Tupla contendo (ano, mês) como inteiros.
    """
    try:
        partes = data_planejamento.split('/')
        ano = int(partes[0])
        mes_str = partes[1].lower()
        mes = MESES.get(mes_str, 0)
        return ano, mes
    except Exception as e:
        print(f"Erro ao extrair mês e ano de '{data_planejamento}': {e}")
        return 0, 0

def extrair_mes_ano_recebimento(data_recebimento: str) -> Tuple[int, int]:
    """
    Extrai o mês e o ano da data de recebimento.
    
    Args:
        data_recebimento: String representando a data de recebimento.
        
    Returns:
        Tupla contendo (ano, mês) como inteiros.
    """
    try:
        # Tenta diferentes formatos de data
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                data = datetime.strptime(data_recebimento, fmt)
                return data.year, data.month
            except ValueError:
                continue
        
        # Se nenhum formato funcionar, levanta exceção
        raise ValueError(f"Formato de data não reconhecido: {data_recebimento}")
    except Exception as e:
        print(f"Erro ao extrair mês e ano de '{data_recebimento}': {e}")
        return 0, 0

def validar_nota_fiscal(uf: str, nfe: int, pedido: int, base_dados: pd.DataFrame) -> bool:
    """
    Verifica se a combinação de UF, NFe e Pedido existe na base de dados.
    
    Args:
        uf: Unidade Federativa da nota fiscal.
        nfe: Número da nota fiscal.
        pedido: Número do pedido.
        base_dados: DataFrame contendo a base de dados de notas fiscais.
        
    Returns:
        True se a combinação existir na base de dados, False caso contrário.
    """
    # Converte os tipos para garantir a comparação correta
    nfe = int(nfe)
    pedido = int(pedido)
    
    # Filtra o DataFrame para encontrar a combinação
    filtro = (base_dados['UF'] == uf) & (base_dados['Nfe'] == nfe) & (base_dados['Pedido'] == pedido)
    return filtro.any()

def obter_data_planejamento(uf: str, nfe: int, pedido: int, base_dados: pd.DataFrame) -> str:
    """
    Obtém a data de planejamento para uma combinação de UF, NFe e Pedido.
    
    Args:
        uf: Unidade Federativa da nota fiscal.
        nfe: Número da nota fiscal.
        pedido: Número do pedido.
        base_dados: DataFrame contendo a base de dados de notas fiscais.
        
    Returns:
        String contendo a data de planejamento ou string vazia se não encontrada.
    """
    # Converte os tipos para garantir a comparação correta
    nfe = int(nfe)
    pedido = int(pedido)
    
    # Filtra o DataFrame para encontrar a combinação
    filtro = (base_dados['UF'] == uf) & (base_dados['Nfe'] == nfe) & (base_dados['Pedido'] == pedido)
    resultado = base_dados[filtro]
    
    if not resultado.empty:
        return resultado['Planejamento'].iloc[0]
    return ""

def verificar_abertura_jira(data_planejamento: str, data_recebimento: str) -> str:
    """
    Verifica se um JIRA deve ser aberto imediatamente ou após o fechamento do mês.
    
    Critério: Se o mês e ano da data de planejamento forem menores ou iguais aos da data 
    de recebimento, então "Pode abrir JIRA", caso contrário "Abrir JIRA após o fechamento do mês".
    
    Args:
        data_planejamento: String no formato 'AAAA/mês' (ex: '2025/maio').
        data_recebimento: String representando a data de recebimento.
        
    Returns:
        String indicando se pode abrir JIRA ou se deve esperar.
    """
    ano_plan, mes_plan = extrair_mes_ano_planejamento(data_planejamento)
    ano_rec, mes_rec = extrair_mes_ano_recebimento(data_recebimento)
    
    # Verifica se a extração foi bem-sucedida
    if ano_plan == 0 or mes_plan == 0 or ano_rec == 0 or mes_rec == 0:
        return "Erro na validação das datas"
    
    # Aplica o critério de decisão
    if (ano_plan < ano_rec) or (ano_plan == ano_rec and mes_plan <= mes_rec):
        return "Pode abrir JIRA"
    else:
        return "Abrir JIRA após o fechamento do mês"

def processar_validacao(uf: str, nfe: str, pedido: str, data_recebimento: str, 
                    caminho_base: str) -> Dict[str, Any]:
    """
    Processa a validação completa de uma nota fiscal.
    
    Args:
        uf: Unidade Federativa da nota fiscal.
        nfe: Número da nota fiscal.
        pedido: Número do pedido.
        data_recebimento: Data de recebimento da nota fiscal.
        caminho_base: Caminho para o arquivo Excel contendo a base de dados.
        
    Returns:
        Dicionário contendo o resultado da validação e informações adicionais.
    """
    resultado = {
        'uf': uf,
        'nfe': nfe,
        'pedido': pedido,
        'data_recebimento': data_recebimento,
        'valido': False,
        'data_planejamento': '',
        'decisao': '',
        'mensagem': ''
    }
    
    try:
        # Converte nfe e pedido para inteiros para validação
        try:
            nfe_int = int(nfe)
            pedido_int = int(pedido)
        except ValueError:
            resultado['mensagem'] = "NFe e Pedido devem ser números inteiros"
            return resultado
        
        # Filtro para dados de teste - não processa se for 999999
        if nfe_int == 999999 or pedido_int == 999999:
            resultado['mensagem'] = "Dados de teste (999999) não são processados"
            return resultado
        
        # Carrega a base de dados
        base_dados = carregar_base_dados(caminho_base)
        if base_dados.empty:
            resultado['mensagem'] = "Erro ao carregar a base de dados"
            return resultado
        
        # Valida a existência da nota fiscal na base
        if not validar_nota_fiscal(uf, nfe_int, pedido_int, base_dados):
            resultado['mensagem'] = "Combinação de UF, NFe e Pedido não encontrada na base de dados"
            return resultado
        
        # Obtém a data de planejamento
        data_planejamento = obter_data_planejamento(uf, nfe_int, pedido_int, base_dados)
        if not data_planejamento:
            resultado['mensagem'] = "Data de planejamento não encontrada"
            return resultado
        
        # Verifica se deve abrir JIRA
        decisao = verificar_abertura_jira(data_planejamento, data_recebimento)
        
        # Atualiza o resultado
        resultado['valido'] = True
        resultado['data_planejamento'] = data_planejamento
        resultado['decisao'] = decisao
        resultado['mensagem'] = "Validação concluída com sucesso"
        
    except Exception as e:
        resultado['mensagem'] = f"Erro durante o processamento: {str(e)}"
    
    return resultado

if __name__ == "__main__":
    # Exemplo de uso
    import os
    caminho_data = os.path.join(os.path.dirname(__file__), 'data')  # Define caminho_data
    base_path = os.path.join(caminho_data, 'Base_de_notas.xlsx')    # Caminho correto para qualquer SO
    
    # Teste com um exemplo válido da sua base
    resultado = processar_validacao("RN", "15733", "75710", "2025-05-15", base_path)
    print(resultado)
