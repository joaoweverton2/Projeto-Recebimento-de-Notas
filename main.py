"""
Aplicação principal para o Sistema de Verificação de Notas Fiscais
"""

import os
import sys
import pandas as pd
from datetime import datetime
# import pytz # Comentado pois não será usado para a data de recebimento
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path

# Configurações da aplicação
app = Flask(__name__)

# Configurar timezone padrão (mantido caso seja útil para outras partes, mas não para data_recebimento)
# app.config['TIMEZONE'] = pytz.timezone('America/Sao_Paulo')

# Configurações de caminhos
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

# Importação do módulo de validação
from validacao_nfe import processar_validacao, salvar_registro, exportar_registros_para_excel

# Configuração de caminho de upload (mantido relativo à aplicação)
app.config['UPLOAD_FOLDER'] = BASE_DIR / 'uploads'
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

# Caminho absoluto fornecido pelo usuário para dados
# Usando string raw (r"...") para evitar problemas com barras invertidas no Windows
USER_DATA_PATH = r"C:\Users\joao.miranda\OneDrive - VIDEOMAR REDE NORDESTE S A\Área de Trabalho\Projeto-Recebimento-de-Notas\data"

# Configuração dos caminhos para base e registros usando o caminho do usuário
app.config['BASE_NOTAS'] = os.path.join(USER_DATA_PATH, 'Base_de_notas.xlsx')
app.config['REGISTROS_CSV'] = os.path.join(USER_DATA_PATH, 'registros.csv')
app.config['REGISTROS_EXCEL'] = os.path.join(USER_DATA_PATH, 'registros.xlsx')

# VERIFICAÇÃO DOS CAMINHOS CONFIGURADOS
print("\n" + "="*50)
print(f"📂 Diretório base da aplicação: {BASE_DIR}")
print(f"📦 Diretório de dados configurado: {USER_DATA_PATH}")
print(f"📝 Arquivo base de notas: {app.config['BASE_NOTAS']}")
print(f"🔍 Arquivo base existe? {os.path.exists(app.config['BASE_NOTAS'])}")
print(f"📄 Arquivo CSV de registros: {app.config['REGISTROS_CSV']}")
print(f"📊 Arquivo Excel de registros: {app.config['REGISTROS_EXCEL']}")
print("="*50 + "\n")

# Rotas
@app.route('/')
def index():
    """Rota principal que renderiza a página inicial."""
    return render_template('index.html')

@app.route('/verificar', methods=['POST'])
def verificar():
    """
    Processa a requisição de verificação de nota fiscal.
    Recebe os dados do formulário, valida contra a base de dados,
    determina se um JIRA deve ser aberto e salva o registro.
    Retorna JSON com o resultado da verificação.
    """
    try:
        # Obter dados do formulário
        uf = request.form.get('uf', '').strip().upper()
        nfe = request.form.get('nfe', '').strip()
        pedido = request.form.get('pedido', '').strip()
        data_recebimento_str = request.form.get('data_recebimento', '').strip()

        # Validar formato da data (AAAA-MM-DD)
        try:
            datetime.strptime(data_recebimento_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'valido': False,
                'mensagem': f'Formato inválido para Data de Recebimento. Use AAAA-MM-DD.'
            })

        # Processar a validação passando a string da data como recebida
        resultado = processar_validacao(
            uf, nfe, pedido,
            data_recebimento_str,  # Passa a string original
            app.config['BASE_NOTAS']
        )

        # Se a validação for bem-sucedida, salvar o registro
        if resultado.get('valido'): # Usar .get para segurança
            # Adicionar timestamp da operação ao registro
            resultado['timestamp_operacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Salvar o registro no arquivo CSV (o dict 'resultado' já contém a data_recebimento original)
            salvar_registro(resultado, app.config['REGISTROS_CSV'])

            # Exportar para Excel se o arquivo CSV existir
            if os.path.exists(app.config['REGISTROS_CSV']):
                exportar_registros_para_excel(
                    app.config['REGISTROS_CSV'], app.config['REGISTROS_EXCEL']
                )

        # Retornar o resultado completo da validação
        # O campo 'data_recebimento' no JSON será a string original
        return jsonify(resultado)

    except Exception as e:
        # Log do erro no servidor para depuração
        print(f"Erro na rota /verificar: {str(e)}") 
        return jsonify({
            'valido': False,
            'mensagem': f'Erro interno durante o processamento. Verifique os logs do servidor.'
        })

@app.route('/download/registros', methods=['GET'])
def download_registros():
    """
    Permite o download do arquivo de registros em formato Excel.
    """
    try:
        caminho_arquivo_excel = app.config['REGISTROS_EXCEL']
        # Verificar se o arquivo existe no caminho configurado
        if not os.path.exists(caminho_arquivo_excel):
            return jsonify({
                'sucesso': False,
                'mensagem': f'Arquivo de registros não encontrado em {caminho_arquivo_excel}'
            }), 404

        # Enviar o arquivo para download
        return send_file(
            caminho_arquivo_excel,
            as_attachment=True,
            download_name='registros_notas_fiscais.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        print(f"Erro na rota /download/registros: {str(e)}")
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao baixar o arquivo: {str(e)}'
        }), 500

@app.route('/atualizar-base', methods=['POST'])
def atualizar_base():
    """
    Atualiza a base de dados de notas fiscais (Base_de_notas.xlsx) no caminho configurado.
    """
    try:
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo selecionado'}), 400

        if not arquivo.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'sucesso': False, 'mensagem': 'O arquivo deve ser um Excel (.xlsx ou .xls)'}), 400

        # Salvar o arquivo no caminho configurado, sobrescrevendo o existente
        caminho_destino = app.config['BASE_NOTAS']
        try:
            arquivo.save(caminho_destino)
            print(f"Base de dados atualizada com sucesso em: {caminho_destino}")
            return jsonify({'sucesso': True, 'mensagem': 'Base de dados atualizada com sucesso!'})
        except Exception as save_error:
            print(f"Erro ao salvar o arquivo da base de dados em {caminho_destino}: {save_error}")
            return jsonify({'sucesso': False, 'mensagem': f'Erro ao salvar o arquivo no servidor: {save_error}'}), 500

    except Exception as e:
        print(f"Erro na rota /atualizar-base: {str(e)}")
        return jsonify({'sucesso': False, 'mensagem': f'Erro interno ao atualizar a base: {str(e)}'}), 500

@app.route('/admin')
def admin():
    """Rota para a página de administração."""
    return render_template('admin.html')

if __name__ == '__main__':
    # Verifica se o diretório de dados existe (não tenta criar)
    if not os.path.isdir(USER_DATA_PATH):
        print(f"\nAVISO IMPORTANTE: O diretório de dados configurado NÃO existe ou não é um diretório:")
        print(f"'{USER_DATA_PATH}'")
        print("A aplicação pode não funcionar corretamente sem este diretório e seus arquivos.")
        print("Certifique-se de que o caminho está correto e acessível.")
    else:
        print(f"\nDiretório de dados '{USER_DATA_PATH}' encontrado.")

    print("\nIniciando a aplicação Flask...")
    # Executa o servidor Flask
    # host='0.0.0.0' permite acesso de outras máquinas na rede
    # debug=True é útil para desenvolvimento, mas desative em produção
    app.run(host='0.0.0.0', port=5000, debug=True)

