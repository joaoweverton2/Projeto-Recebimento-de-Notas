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
# import pytz # Removido pois não está sendo usado diretamente aqui

# Configurar locale para português brasileiro
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
    except:
        pass  # Se não conseguir configurar o locale, usaremos uma abordagem alternativa

# --- REMOVIDO --- 
# A variável caminho_data não é usada pelas funções principais,
# que recebem o caminho correto de main.py.
# caminho_data = r"C:\Users\joao.miranda\OneDrive - VIDEOMAR REDE NORDESTE S A\Área de Trabalho\Projeto-Recebimento-de-Notas\data"
# --- FIM DA REMOÇÃO ---

# Mapeamento de nomes de meses em português para números
MESES = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
    'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

def carregar_base_dados(caminho_arquivo: str) -> pd.DataFrame:
    """
    Carrega a base de dados de notas fiscais a partir de um arquivo Excel.

    Args:
        caminho_arquivo: Caminho para o arquivo Excel contendo a base de dados.

    Returns:
        DataFrame contendo os dados das notas fiscais.
    """
    try:
        # Verifica se o arquivo existe antes de tentar ler
        if not os.path.isfile(caminho_arquivo):
            print(f"Erro: Arquivo da base de dados não encontrado em: {caminho_arquivo}")
            return pd.DataFrame() # Retorna DataFrame vazio se não encontrar
        return pd.read_excel(caminho_arquivo)
    except Exception as e:
        print(f"Erro ao carregar a base de dados de {caminho_arquivo}: {e}")
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
        if mes == 0:
            print(f"Aviso: Mês não reconhecido em '{data_planejamento}'")
        return ano, mes
    except Exception as e:
        print(f"Erro ao extrair mês e ano de '{data_planejamento}': {e}")
        return 0, 0

def extrair_mes_ano_recebimento(data_recebimento: str) -> Tuple[int, int]:
    """
    Extrai o mês e o ano da data de recebimento.

    Args:
        data_recebimento: String representando a data de recebimento (espera AAAA-MM-DD).

    Returns:
        Tupla contendo (ano, mês) como inteiros.
    """
    try:
        # Prioriza o formato esperado AAAA-MM-DD
        data = datetime.strptime(data_recebimento, '%Y-%m-%d')
        return data.year, data.month
    except ValueError:
        # Tenta outros formatos comuns como fallback
        for fmt in ['%d/%m/%Y', '%d-%m-%Y']:
            try:
                data = datetime.strptime(data_recebimento, fmt)
                print(f"Aviso: Data de recebimento '{data_recebimento}' estava em formato inesperado, mas foi convertida.")
                return data.year, data.month
            except ValueError:
                continue
        # Se nenhum formato funcionar, loga o erro e retorna 0,0
        print(f"Erro: Formato de data não reconhecido para '{data_recebimento}'. Use AAAA-MM-DD.")
        return 0, 0
    except Exception as e:
        print(f"Erro inesperado ao extrair mês e ano de '{data_recebimento}': {e}")
        return 0, 0

def validar_nota_fiscal(uf: str, nfe: int, pedido: int, base_dados: pd.DataFrame) -> bool:
    if base_dados.empty:
        print("⚠️ Base de dados está vazia!")
        return False
    
    print("\n🔍 Dados recebidos para validação:")
    print(f"UF: '{uf}' | NFe: '{nfe}' | Pedido: '{pedido}'")
    
    print("\n📋 Amostra da base de dados (5 primeiras linhas):")
    print(base_dados.head())
    
    print("\n🔎 Procurando correspondência...")
    try:
        filtro_uf = base_dados['UF'].astype(str).str.strip().str.upper() == str(uf).strip().upper()
        filtro_nfe = base_dados['Nfe'].astype(str).str.strip() == str(nfe).strip()
        filtro_pedido = base_dados['Pedido'].astype(str).str.strip() == str(pedido).strip()
        
        resultado = base_dados[filtro_uf & filtro_nfe & filtro_pedido]
        
        if not resultado.empty:
            print("✅ Correspondência encontrada:")
            print(resultado)
            return True
        else:
            print("❌ Nenhuma correspondência encontrada")
            print("Valores únicos na base:")
            print("UF:", base_dados['UF'].unique())
            print("Nfe:", base_dados['Nfe'].unique()[:10], "...")
            print("Pedido:", base_dados['Pedido'].unique()[:10], "...")
            return False
            
    except Exception as e:
        print(f"🔥 Erro durante a validação: {str(e)}")
        return False

def obter_data_planejamento(uf: str, nfe: int, pedido: int, base_dados: pd.DataFrame) -> str:
    """
    Obtém a data de planejamento para uma combinação de UF, NFe e Pedido.

    Args:
        uf: Unidade Federativa da nota fiscal.
        nfe: Número da nota fiscal (como int).
        pedido: Número do pedido (como int).
        base_dados: DataFrame contendo a base de dados de notas fiscais.

    Returns:
        String contendo a data de planejamento ou string vazia se não encontrada.
    """
    if base_dados.empty:
        return ""
    try:
        # Garante que as colunas existam
        if not all(col in base_dados.columns for col in ['UF', 'Nfe', 'Pedido', 'Planejamento']):
            print("Erro: Colunas 'UF', 'Nfe', 'Pedido' ou 'Planejamento' não encontradas na base.")
            return ""

        # Filtra o DataFrame para encontrar a combinação
        filtro = (
            base_dados['UF'].astype(str).str.upper() == str(uf).upper() &
            base_dados['Nfe'].astype(int) == int(nfe) &
            base_dados['Pedido'].astype(int) == int(pedido)
        )
        resultado = base_dados.loc[filtro]

        if not resultado.empty:
            # Pega o primeiro resultado e garante que seja string
            return str(resultado['Planejamento'].iloc[0])
        return ""
    except Exception as e:
        print(f"Erro ao obter data de planejamento: {e}")
        return ""

def verificar_abertura_jira(data_planejamento: str, data_recebimento: str) -> str:
    """
    Verifica se um JIRA deve ser aberto imediatamente ou após o fechamento do mês.

    Critério: Se o mês e ano da data de planejamento forem menores ou iguais aos da data
    de recebimento, então "Pode abrir JIRA", caso contrário "Abrir JIRA após o fechamento do mês".

    Args:
        data_planejamento: String no formato 'AAAA/mês' (ex: '2025/maio').
        data_recebimento: String representando a data de recebimento (espera AAAA-MM-DD).

    Returns:
        String indicando se pode abrir JIRA ou se deve esperar.
    """
    ano_plan, mes_plan = extrair_mes_ano_planejamento(data_planejamento)
    ano_rec, mes_rec = extrair_mes_ano_recebimento(data_recebimento)

    # Verifica se a extração foi bem-sucedida
    if ano_plan == 0 or mes_plan == 0 or ano_rec == 0 or mes_rec == 0:
        return "Erro na validação das datas (formato inválido ou mês não reconhecido)"

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
        nfe: Número da nota fiscal (como string).
        pedido: Número do pedido (como string).
        data_recebimento: Data de recebimento da nota fiscal (string AAAA-MM-DD).
        caminho_base: Caminho para o arquivo Excel contendo a base de dados.

    Returns:
        Dicionário contendo o resultado da validação e informações adicionais.
    """
    resultado = {
        'uf': uf,
        'nfe': nfe,
        'pedido': pedido,
        'data_recebimento': data_recebimento, # Mantém a string original
        'valido': False,
        'data_planejamento': '',
        'decisao': '',
        'mensagem': ''
    }

    try:
        # Carrega a base de dados
        base_dados = carregar_base_dados(caminho_base)
        if base_dados.empty:
            resultado['mensagem'] = f"Erro ao carregar ou base de dados vazia em '{caminho_base}'"
            return resultado

        # Converte nfe e pedido para inteiros para validação
        try:
            nfe_int = int(nfe)
            pedido_int = int(pedido)
        except ValueError:
            resultado['mensagem'] = "NFe e Pedido devem ser números inteiros"
            return resultado

        # Valida a existência da nota fiscal na base
        if not validar_nota_fiscal(uf, nfe_int, pedido_int, base_dados):
            resultado['mensagem'] = "Combinação de UF, NFe e Pedido não encontrada na base de dados"
            return resultado

        # Obtém a data de planejamento
        data_planejamento = obter_data_planejamento(uf, nfe_int, pedido_int, base_dados)
        if not data_planejamento:
            resultado['mensagem'] = "Data de planejamento não encontrada para esta combinação"
            # Considera inválido se não achar planejamento?
            # resultado['valido'] = False # Descomente se for requisito
            return resultado # Retorna aqui ou continua para decisão?

        # Verifica se deve abrir JIRA
        decisao = verificar_abertura_jira(data_planejamento, data_recebimento)

        # Atualiza o resultado final
        resultado['valido'] = True
        resultado['data_planejamento'] = data_planejamento
        resultado['decisao'] = decisao
        resultado['mensagem'] = "Validação concluída com sucesso"

    except Exception as e:
        print(f"Erro inesperado durante processar_validacao: {e}")
        resultado['mensagem'] = f"Erro interno durante o processamento: {str(e)}"

    return resultado

def salvar_registro(dados: Dict[str, Any], caminho_arquivo: str) -> bool:
    """
    Salva os dados de uma validação em um arquivo CSV.

    Args:
        dados: Dicionário contendo os dados da validação.
        caminho_arquivo: Caminho para o arquivo CSV onde os dados serão salvos.

    Returns:
        True se o salvamento for bem-sucedido, False caso contrário.
    """
    try:
        # Define a ordem das colunas desejada
        colunas = ['uf', 'nfe', 'pedido', 'data_recebimento', 'valido', 
                'data_planejamento', 'decisao', 'mensagem', 'timestamp_operacao']
        # Cria um DataFrame com os dados, garantindo a ordem e incluindo colunas faltantes com None
        df = pd.DataFrame([dados], columns=colunas)

        # Verifica se o arquivo já existe para decidir se escreve o cabeçalho
        arquivo_existe = os.path.isfile(caminho_arquivo)

        # Salva os dados (append se o arquivo já existir, sem cabeçalho)
        df.to_csv(caminho_arquivo, mode='a', header=not arquivo_existe, index=False, encoding='utf-8')

        print(f"Registro salvo com sucesso em: {caminho_arquivo}")
        return True
    except Exception as e:
        print(f"Erro ao salvar registro em {caminho_arquivo}: {e}")
        return False

def exportar_registros_para_excel(caminho_csv: str, caminho_excel: str) -> bool:
    """
    Exporta os registros de um arquivo CSV para um arquivo Excel.

    Args:
        caminho_csv: Caminho para o arquivo CSV contendo os registros.
        caminho_excel: Caminho para o arquivo Excel onde os registros serão salvos.

    Returns:
        True se a exportação for bem-sucedida, False caso contrário.
    """
    try:
        # Verifica se o arquivo CSV existe
        if not os.path.isfile(caminho_csv):
            print(f"Arquivo CSV não encontrado para exportação: {caminho_csv}")
            return False

        # Carrega os dados do CSV
        df = pd.read_csv(caminho_csv, encoding='utf-8')

        # Salva os dados em um arquivo Excel
        df.to_excel(caminho_excel, index=False)

        print(f"Registros exportados para Excel com sucesso em: {caminho_excel}")
        return True
    except Exception as e:
        print(f"Erro ao exportar registros de {caminho_csv} para Excel {caminho_excel}: {e}")
        return False

# Função principal para testes (não será executada quando importada por main.py)
if __name__ == "__main__":
    print("\nExecutando testes locais do módulo validacao_nfe.py...")
    # Define um caminho relativo para a pasta 'data' a partir deste script
    # Assume que o script está na raiz do projeto
    script_dir = os.path.dirname(__file__)
    teste_data_dir = os.path.join(script_dir, 'data')
    teste_base_path = os.path.join(teste_data_dir, 'Base_de_notas.xlsx')
    teste_registros_csv = os.path.join(teste_data_dir, 'registros_teste.csv')
    teste_registros_excel = os.path.join(teste_data_dir, 'registros_teste.xlsx')

    print(f"Usando base de teste: {teste_base_path}")

    # Exemplo de validação bem-sucedida (ajuste os valores se necessário)
    resultado_ok = processar_validacao(
        uf="RN",
        nfe="15733",
        pedido="75710",
        data_recebimento="2025-05-15",
        caminho_base=teste_base_path
    )
    print("\nResultado Validação OK:", resultado_ok)
    if resultado_ok.get('valido'):
        resultado_ok['timestamp_operacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        salvar_registro(resultado_ok, teste_registros_csv)
        exportar_registros_para_excel(teste_registros_csv, teste_registros_excel)

    # Exemplo de validação com falha (NFe não encontrada)
    resultado_falha = processar_validacao(
        uf="SP",
        nfe="99999",
        pedido="12345",
        data_recebimento="2025-05-20",
        caminho_base=teste_base_path
    )
    print("\nResultado Validação Falha:", resultado_falha)
    if resultado_falha.get('valido'): # Não deve entrar aqui
        resultado_falha['timestamp_operacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        salvar_registro(resultado_falha, teste_registros_csv)

    print("\nTestes locais concluídos.")

