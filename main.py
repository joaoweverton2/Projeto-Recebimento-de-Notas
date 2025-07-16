from flask import Flask, request, jsonify, send_file, send_from_directory
from pathlib import Path
import os
from datetime import datetime
import logging
from database import DatabaseManager
from validacao_nfe import ValidadorNFE
from io import BytesIO
import pandas as pd

# Configuração básica
app = Flask(__name__, static_folder='static')
app.config.update({
    'UPLOAD_FOLDER': Path('static/uploads'),
    'DATABASE_FOLDER': Path('data'),
    'BASE_NOTAS': Path('data/Base_de_notas.xlsx'),
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'GOOGLE_CREDENTIALS_BASE64': os.getenv('GOOGLE_CREDENTIALS_BASE64'),
    'GOOGLE_SHEET_ID': os.getenv('GOOGLE_SHEET_ID')
})

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicialização de serviços
try:
    # Garante que os diretórios existam
    app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
    app.config['DATABASE_FOLDER'].mkdir(parents=True, exist_ok=True)
    
    # Inicializa serviços
    validador = ValidadorNFE(str(app.config['BASE_NOTAS']))
    db = DatabaseManager(app)
    
    logger.info("Serviços inicializados com sucesso")
except Exception as e:
    logger.critical(f"Falha na inicialização: {str(e)}")
    raise

# Rota para servir arquivos estáticos
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# Rota principal
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# Rota de administração
@app.route('/admin')
def admin():
    return send_from_directory(app.static_folder, 'admin.html')

# Rotas da API
@app.route('/verificar', methods=['POST'])
def verificar_nota():
    """Endpoint para validação de notas fiscais"""
    try:
        dados = {
            'uf': request.form.get('uf', '').strip().upper(),
            'nfe': request.form.get('nfe', '').strip(),
            'pedido': request.form.get('pedido', '').strip(),
            'data_recebimento': request.form.get('data_recebimento', '').strip()
        }

        logger.info(f"Dados recebidos: {dados}")

        if not all(dados.values()):
            return jsonify({
                'valido': False,
                'mensagem': 'Todos os campos são obrigatórios'
            }), 400

        resultado = validador.validar(**dados)

        if resultado.get('valido'):
            try:
                db.criar_registro({
                    'uf': resultado['uf'],
                    'nfe': resultado['nfe'],
                    'pedido': resultado['pedido'],
                    'data_recebimento': resultado['data_recebimento'],
                    'valido': True,
                    'data_planejamento': resultado['data_planejamento'],
                    'decisao': resultado['decisao'],
                    'mensagem': resultado['mensagem']
                })
            except Exception as e:
                logger.error(f"Erro ao salvar registro: {str(e)}")
                resultado['mensagem'] = f"Validação ok, mas erro no registro: {str(e)}"

        return jsonify(resultado), 200 if resultado['valido'] else 400

    except Exception as e:
        logger.error(f"Erro em /verificar: {str(e)}")
        return jsonify({
            'valido': False,
            'error': 'Erro interno no servidor',
            'mensagem': str(e)
        }), 500

@app.route('/atualizar-base', methods=['POST'])
def atualizar_base():
    """Endpoint para atualização do arquivo base"""
    try:
        if 'arquivo' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'error': 'Nome de arquivo inválido'}), 400

        if not arquivo.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Formato inválido (use .xlsx ou .xls)'}), 400

        arquivo.save(app.config['BASE_NOTAS'])
        global validador
        validador = ValidadorNFE(str(app.config['BASE_NOTAS']))

        return jsonify({'success': True, 'message': 'Base de dados atualizada com sucesso'}), 200

    except Exception as e:
        logger.error(f"Erro em /atualizar-base: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-registros', methods=['GET'])
def download_registros():
    """Endpoint para exportar registros como Excel"""
    try:
        registros = db.listar_registros()
        df = pd.DataFrame(registros)
        
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name='registros_notas_fiscais.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Erro em /download-registros: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


