"""
API Principal - Versão 3.1
Correções aplicadas:
1. Tratamento completo de erros
2. Validação de entrada robusta
3. Integração correta com validador e database
4. Endpoints documentados
"""

from flask import Flask, request, jsonify, send_file
from pathlib import Path
import os
from datetime import datetime
import logging
from validacao_nfe import ValidadorNFE
from database import DatabaseManager

# Configuração básica
app = Flask(__name__)
app.config.update({
    'UPLOAD_FOLDER': Path('uploads'),
    'DATABASE_FOLDER': Path('data'),
    'BASE_NOTAS': Path('data/Base_de_notas.xlsx'),
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024  # 16MB
})

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicialização de serviços
try:
    validador = ValidadorNFE(str(app.config['BASE_NOTAS']))
    db = DatabaseManager(app)
except Exception as e:
    logger.critical(f"Falha na inicialização: {str(e)}")
    raise

@app.route('/verificar', methods=['POST'])
def verificar_nota():
    """
    Endpoint de validação de notas fiscais
    Requer:
    - uf: string (ex: "SP")
    - nfe: número da nota fiscal
    - pedido: número do pedido
    - data_recebimento: string (formato YYYY-MM-DD)
    """
    try:
        # Extração e validação básica
        dados = {
            'uf': request.form.get('uf', '').strip(),
            'nfe': request.form.get('nfe', '').strip(),
            'pedido': request.form.get('pedido', '').strip(),
            'data_recebimento': request.form.get('data_recebimento', '').strip()
        }

        logger.info(f"Dados recebidos: {dados}")

        # Validação completa
        resultado = validador.validar(**dados)

        # Se válido, registra no banco
        if resultado.get('valido'):
            try:
                registro = {
                    'uf': resultado['uf'],
                    'nfe': resultado['nfe'],
                    'pedido': resultado['pedido'],
                    'data_recebimento': resultado['data_recebimento'],
                    'valido': True,
                    'data_planejamento': resultado.get('data_planejamento', ''),
                    'decisao': resultado.get('decisao', ''),
                    'mensagem': resultado.get('mensagem', '')
                }
                db.criar_registro(registro)
            except Exception as e:
                logger.error(f"Erro ao salvar registro: {str(e)}")
                resultado['mensagem'] = f"Validação ok, mas erro no registro: {str(e)}"

        return jsonify(resultado), 200 if resultado['valido'] else 400

    except Exception as e:
        logger.error(f"Erro em /verificar: {str(e)}")
        return jsonify({
            'error': 'Erro interno',
            'detalhes': str(e)
        }), 500

@app.route('/atualizar-base', methods=['POST'])
def atualizar_base():
    """Endpoint para atualizar o arquivo base de notas"""
    try:
        if 'arquivo' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'error': 'Nome de arquivo inválido'}), 400

        if not arquivo.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Formato inválido (use .xlsx ou .xls)'}), 400

        # Garante que o diretório existe
        app.config['DATABASE_FOLDER'].mkdir(exist_ok=True)

        # Salva o arquivo
        arquivo.save(app.config['BASE_NOTAS'])
        
        # Recarrega o validador
        global validador
        validador = ValidadorNFE(str(app.config['BASE_NOTAS']))

        return jsonify({'success': True}), 200

    except Exception as e:
        logger.error(f"Erro em /atualizar-base: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-registros', methods=['GET'])
def download_registros():
    """Exporta registros para Excel"""
    try:
        registros = db.listar_registros()
        df = pd.DataFrame(registros)
        
        output_path = app.config['DATABASE_FOLDER'] / 'registros_exportados.xlsx'
        df.to_excel(output_path, index=False)
        
        return send_file(
            output_path,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Erro em /download-registros: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


