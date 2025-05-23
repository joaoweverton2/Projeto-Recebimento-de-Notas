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

# Configurar o timezone padrão para todas as operações
import time
time.tzset = lambda: None  # Desativa a mudança de timezone global (para evitar efeitos colaterais)

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
    try:
        # Obter dados como JSON
        dados = request.get_json()
        
        uf = dados.get('uf', '').strip().upper()
        nfe = dados.get('nfe', '').strip()
        pedido = dados.get('pedido', '').strip()
        data_recebimento_str = dados.get('data_recebimento', '').strip()
        
        # Processar a validação (agora recebendo DD/MM/YYYY)
        resultado = processar_validacao(
            uf, nfe, pedido, 
            data_recebimento_str,  # Já está no formato DD/MM/YYYY
            app.config['BASE_NOTAS']
        )
        
        # Converter a data de DD/MM/YYYY para objeto datetime
        try:
            # Primeiro tenta interpretar como DD/MM/YYYY
            dia, mes, ano = map(int, data_recebimento_str.split('/'))
            if mes > 12 or dia > 31:  # Validação básica
                raise ValueError
            data_naive = datetime(ano, mes, dia)
        except (ValueError, AttributeError):
            return jsonify({
                'valido': False,
                'mensagem': 'Formato de data inválido. Use DD/MM/AAAA com valores válidos'
            })
        
        # Aplicar timezone de Brasília
        tz = pytz.timezone('America/Sao_Paulo')
        data_brasilia = tz.localize(data_naive)
        
        # Processar a validação (enviar como string no formato YYYY-MM-DD)
        resultado = processar_validacao(
            uf, nfe, pedido, 
            data_brasilia.strftime('%Y-%m-%d'),
            app.config['BASE_NOTAS']
        )
        
        # Formatando a data de volta para DD/MM/YYYY no resultado
        if 'data_recebimento' in resultado:
            data_obj = datetime.strptime(resultado['data_recebimento'], '%Y-%m-%d')
            resultado['data_recebimento'] = data_obj.strftime('%d/%m/%Y')
        
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