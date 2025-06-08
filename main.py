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
from database import DatabaseManager

# Configurações da aplicação
app = Flask(__name__)

# Configurações (mantenha as existentes)
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))
app.config['UPLOAD_FOLDER'] = BASE_DIR / 'uploads'
app.config['DATABASE_FOLDER'] = BASE_DIR / 'data'
app.config['BASE_NOTAS'] = BASE_DIR / 'data' / 'Base_de_notas.xlsx'
app.config['REGISTROS_EXCEL'] = BASE_DIR / 'data' / 'registros.xlsx'
app.config['REGISTROS_DB'] = BASE_DIR / 'data' / 'registros.db'

# Crie a instância do DatabaseManager
db_manager = DatabaseManager(app.config['REGISTROS_DB'])

# Rota para inicialização (opcional - pode ser chamada uma vez)
@app.route('/init-db')
def init_db():
    """Rota para inicializar o banco de dados"""
    try:
        # Importar dados do Excel se existir
        if os.path.exists(app.config['REGISTROS_EXCEL']):
            success = db_manager.import_from_excel(app.config['REGISTROS_EXCEL'])
            if success:
                count = db_manager.get_record_count()
                return jsonify({
                    'success': True,
                    'message': f'Banco de dados inicializado com {count} registros'
                })
        return jsonify({
            'success': False,
            'message': 'Arquivo de registros não encontrado'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        })

# Configurar timezone padrão
app.config['TIMEZONE'] = pytz.timezone('America/Sao_Paulo')

# Garantir que a pasta data existe e tem permissões
data_dir = os.path.join(BASE_DIR, 'data')
os.makedirs(data_dir, exist_ok=True)
os.chmod(data_dir, 0o777)  # Permissões amplas (ajuste conforme necessidade de segurança)

# Importação do módulo de validação
from validacao_nfe import processar_validacao

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
        # Converter para datetime SEM timezone primeiro
        data_naive = datetime.strptime(data_recebimento_str, '%Y-%m-%d')
        # Adicionar timezone (Brasília)
        data_com_timezone = app.config['TIMEZONE'].localize(data_naive)
        # Converter para UTC para armazenamento
        data_utc = data_com_timezone.astimezone(pytz.UTC)
        
        # Processar a validação (enviar como string formatada)
        resultado = processar_validacao(
            uf, nfe, pedido, 
            data_recebimento_str, # Usa a string original
            app.config['BASE_NOTAS']
        )
        
        # Se a validação for bem-sucedida, salvar o registro no SQLite
        if resultado['valido']:
            # Garanta que está passando TODOS os campos necessários
            dados_registro = {
                'uf': uf,
                'nfe': nfe,
                'pedido': pedido,
                'data_recebimento': data_recebimento_str,
                'valido': True,
                'data_planejamento': resultado.get('data_planejamento', ''),
                'decisao': resultado.get('decisao', ''),
                'mensagem': resultado.get('mensagem', ''),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if not db_manager.save_verification(dados_registro):
                logger.error("Falha ao salvar no banco de dados")
            
        return jsonify(resultado)
    
    except Exception as e:
        logger.error(f"Erro na verificação: {e}")
        return jsonify({'valido': False, 'mensagem': str(e)})
    
@app.route('/download/registros', methods=['GET'])
def download_registros():
    try:
        # Exportar para Excel temporário
        temp_excel = app.config['DATABASE_FOLDER'] / 'registros_exportados.xlsx'
        
        # Exporta os dados
        if db_manager.export_to_excel(str(temp_excel)):
            return send_file(
                str(temp_excel),
                as_attachment=True,
                download_name='registros_notas_fiscais.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        return jsonify({
            'sucesso': False,
            'mensagem': 'Falha ao gerar arquivo Excel'
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao baixar o arquivo: {str(e)}'
        })

# Adicione esta rota para verificação
@app.route('/check-db')
def check_db():
    """Rota para verificar o status do banco de dados"""
    try:
        count = db_manager.get_record_count()
        return jsonify({
            'total_registros': count,
            'database_path': str(app.config['REGISTROS_DB']),
            'status': 'OK'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'ERROR'
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