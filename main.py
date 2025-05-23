"""
Aplicação principal para o Sistema de Verificação de Notas Fiscais

Este módulo contém a aplicação Flask que serve a interface web e processa
as requisições de verificação de notas fiscais.
"""

import os
import sys
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from pathlib import Path
# Adiciona o diretório atual ao PATH do Python
sys.path.append(str(Path(__file__).parent))

# Adicionar o diretório do projeto ao path para importar o módulo de validação
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from validacao_nfe import processar_validacao, salvar_registro, exportar_registros_para_excel

# Configurações da aplicação
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
app.config['DATABASE_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
app.config['BASE_NOTAS'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Base de notas.xlsx')
app.config['REGISTROS_CSV'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'registros.csv')
app.config['REGISTROS_EXCEL'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'registros.xlsx')

# Garantir que os diretórios necessários existam
for folder in [app.config['UPLOAD_FOLDER'], app.config['DATABASE_FOLDER']]:
    os.makedirs(folder, exist_ok=True)
    
# Novo caminho da pasta Data
caminho_data = r"C:\Users\joao.miranda\OneDrive - VIDEOMAR REDE NORDESTE S A\Área de Trabalho\Projeto-Recebimento-de-Notas\data"    

# Copiar a base de notas para o diretório de dados se não existir
if not os.path.exists(app.config['BASE_NOTAS']):
    original_base = f"{caminho_data}\\Base de notas.xlsx"
    if os.path.exists(original_base):
        import shutil
        shutil.copy(original_base, app.config['BASE_NOTAS'])

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
    
    Returns:
        JSON com o resultado da verificação.
    """
    try:
        # Obter dados do formulário
        uf = request.form.get('uf', '').strip().upper()
        nfe = request.form.get('nfe', '').strip()
        pedido = request.form.get('pedido', '').strip()
        data_recebimento = request.form.get('data_recebimento', '').strip()
        
        # Validar dados de entrada
        if not all([uf, nfe, pedido, data_recebimento]):
            return jsonify({
                'valido': False,
                'mensagem': 'Todos os campos são obrigatórios'
            })
        
        # Processar a validação
        resultado = processar_validacao(
            uf, nfe, pedido, data_recebimento, app.config['BASE_NOTAS']
        )
        
        # Se a validação for bem-sucedida, salvar o registro
        if resultado['valido']:
            # Adicionar timestamp ao registro
            resultado['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Salvar o registro no arquivo CSV
            salvar_registro(resultado, app.config['REGISTROS_CSV'])
            
            # Exportar para Excel se o arquivo CSV existir
            if os.path.exists(app.config['REGISTROS_CSV']):
                exportar_registros_para_excel(
                    app.config['REGISTROS_CSV'], app.config['REGISTROS_EXCEL']
                )
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({
            'valido': False,
            'mensagem': f'Erro durante o processamento: {str(e)}'
        })

@app.route('/download/registros', methods=['GET'])
def download_registros():
    """
    Permite o download do arquivo de registros em formato Excel.
    
    Returns:
        Arquivo Excel para download.
    """
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(app.config['REGISTROS_EXCEL']):
            return jsonify({
                'sucesso': False,
                'mensagem': 'Arquivo de registros não encontrado'
            })
        
        # Enviar o arquivo para download
        return send_file(
            app.config['REGISTROS_EXCEL'],
            as_attachment=True,
            download_name='registros_notas_fiscais.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao baixar o arquivo: {str(e)}'
        })

@app.route('/atualizar-base', methods=['POST'])
def atualizar_base():
    """
    Atualiza a base de dados de notas fiscais.
    
    Recebe um arquivo Excel enviado pelo usuário e o salva como a nova base de dados.
    
    Returns:
        JSON com o resultado da atualização.
    """
    try:
        # Verificar se o arquivo foi enviado
        if 'arquivo' not in request.files:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum arquivo enviado'
            })
        
        arquivo = request.files['arquivo']
        
        # Verificar se o arquivo tem nome
        if arquivo.filename == '':
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum arquivo selecionado'
            })
        
        # Verificar se é um arquivo Excel
        if not arquivo.filename.endswith(('.xlsx', '.xls')):
            return jsonify({
                'sucesso': False,
                'mensagem': 'O arquivo deve ser um Excel (.xlsx ou .xls)'
            })
        
        # Salvar o arquivo
        filename = secure_filename('Base\ de\ notas.xlsx')
        arquivo.save(app.config['BASE_NOTAS'])
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Base de dados atualizada com sucesso'
        })
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao atualizar a base de dados: {str(e)}'
        })

# Adicionar rota para página de administração
@app.route('/admin')
def admin():
    """Rota para a página de administração."""
    return render_template('admin.html')

if __name__ == '__main__':
    # Executar a aplicação
    app.run(host='0.0.0.0', port=5000, debug=True)
