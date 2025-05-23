"""
Aplicação principal para o Sistema de Verificação de Notas Fiscais
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import pytz
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path

# Configurações da aplicação
app = Flask(__name__)

# Configurar timezone padrão
app.config['TIMEZONE'] = pytz.timezone('America/Sao_Paulo')

# Configurações de caminhos ABSOLUTAMENTE CONFIAVEIS
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

# Importação do módulo de validação
from validacao_nfe import processar_validacao, salvar_registro, exportar_registros_para_excel

# Configuração de caminhos usando pathlib (garante funcionamento em qualquer SO)
app.config['UPLOAD_FOLDER'] = BASE_DIR / 'uploads'
app.config['DATABASE_FOLDER'] = BASE_DIR / 'data'
app.config['BASE_NOTAS'] = BASE_DIR / 'data' / 'Base_de_notas.xlsx'
app.config['REGISTROS_CSV'] = BASE_DIR / 'data' / 'registros.csv'
app.config['REGISTROS_EXCEL'] = BASE_DIR / 'data' / 'registros.xlsx'

# Garantir que os diretórios existam (cria se não existirem)
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['DATABASE_FOLDER'].mkdir(exist_ok=True)

# VERIFICAÇÃO CRUCIAL DO ARQUIVO (adicionado)
print("\n" + "="*50)
print(f"📂 Diretório base: {BASE_DIR}")
print(f"📝 Arquivo de notas: {app.config['BASE_NOTAS']}")
print(f"🔍 Arquivo existe? {app.config['BASE_NOTAS'].exists()}")
print("="*50 + "\n")

# Rotas existentes (mantenha todas as suas rotas como estão)
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
        data_recebimento_str = request.form.get('data_recebimento', '').strip()
        data_recebimento = datetime.strptime(data_recebimento_str, '%Y-%m-%d')
        data_recebimento = app.config['TIMEZONE'].localize(data_recebimento)
        
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
        filename = secure_filename('Base_de_notas.xlsx')
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
    # DEBUG EXTRA - Mostra estrutura de arquivos
    print("\nESTRUTURA DE ARQUIVOS:")
    for root, dirs, files in os.walk(BASE_DIR):
        print(f"{root}: {files}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)