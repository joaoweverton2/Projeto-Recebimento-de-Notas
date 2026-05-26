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

# Configuração da aplicação
app.config.update({
    'UPLOAD_FOLDER': Path('static/uploads'),
    'DATABASE_FOLDER': Path('data'),
    'SQLITE_DB_PATH': Path('instance/data/base_notas.db'),
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'GOOGLE_CREDENTIALS_BASE64': os.getenv('GOOGLE_CREDENTIALS_BASE64'),
    'GOOGLE_SHEET_ID': os.getenv('GOOGLE_SHEET_ID')
})

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicialização de serviços
try:
    # Garante que os diretórios existam
    app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
    app.config['DATABASE_FOLDER'].mkdir(parents=True, exist_ok=True)
    
    # Inicializa serviços
    db = DatabaseManager(app)
    validador = ValidadorNFE(db)
    
    logger.info("✅ Serviços inicializados com sucesso")
    logger.info(f"📁 SQLite path: {app.config['SQLITE_DB_PATH']}")
    logger.info(f"📊 Google Sheet ID: {app.config['GOOGLE_SHEET_ID']}")
    
except Exception as e:
    logger.critical(f"❌ Falha na inicialização: {str(e)}")
    raise

# Rotas para arquivos estáticos
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

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

        logger.info(f"📝 Verificando nota: {dados}")

        # Executa a validação
        resultado = validador.validar(**dados)

        # Registra no Google Sheets independente do resultado
        registro = {
            'uf': dados['uf'],
            'nfe': dados['nfe'],
            'pedido': dados['pedido'],
            'data_recebimento': dados['data_recebimento'],
            'data_planejamento': resultado.get('data_planejamento', ''),
            'decisao': resultado['decisao']
        }
        
        try:
            db.criar_registro(registro)
            logger.info(f"✅ Registro salvo: {registro['decisao']}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar registro: {str(e)}")

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"❌ Erro em /verificar: {str(e)}")
        return jsonify({
            'uf': request.form.get('uf', '').strip().upper(),
            'nfe': request.form.get('nfe', '').strip(),
            'pedido': request.form.get('pedido', '').strip(),
            'data_recebimento': request.form.get('data_recebimento', '').strip(),
            'valido': False,
            'data_planejamento': '',
            'decisao': 'Avaliar internamente',
            'mensagem': 'Nota não encontrada. Procure os analistas do PCM!'
        }), 500

@app.route('/atualizar-base', methods=['POST'])
def atualizar_base():
    """Endpoint para atualização do arquivo base (Excel -> Google Sheets + SQLite)"""
    try:
        if 'arquivo' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'error': 'Nome de arquivo inválido'}), 400

        if not arquivo.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Formato inválido. Use arquivos .xlsx ou .xls'}), 400

        # Ler o arquivo Excel
        logger.info(f"📥 Processando arquivo: {arquivo.filename}")
        df_novo = pd.read_excel(arquivo.stream, engine='openpyxl')
        
        # Verifica colunas necessárias
        colunas_necessarias = ["UF", "Nfe", "Pedido", "Planejamento", "Demanda"]
        colunas_faltando = [col for col in colunas_necessarias if col not in df_novo.columns]
        
        if colunas_faltando:
            return jsonify({
                'error': f'Colunas faltando no arquivo: {colunas_faltando}'
            }), 400
        
        # Atualiza tanto Google Sheets quanto SQLite
        db.update_base_notas_data(df_novo)
        
        # Limpa qualquer cache do validador (se existir)
        if hasattr(validador, 'limpar_cache'):
            validador.limpar_cache()
        
        registros_count = len(df_novo)
        logger.info(f"✅ Base atualizada com sucesso! {registros_count} registros carregados")
        
        return jsonify({
            'success': True,
            'message': f'Base de dados atualizada com sucesso! {registros_count} registros carregados.',
            'registros': registros_count
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro em /atualizar-base: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-registros', methods=['GET'])
def download_registros():
    """Endpoint para exportar registros de validações como Excel"""
    try:
        registros = db.listar_registros()
        df = pd.DataFrame(registros)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Registros')
            
            # Ajusta largura das colunas
            worksheet = writer.sheets['Registros']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'registros_notas_fiscais_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"❌ Erro em /download-registros: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar saúde do sistema e consistência dos bancos"""
    try:
        # Verifica saúde dos bancos
        db_status = db.verificar_saude_banco()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'config': {
                'sqlite_path': str(app.config['SQLITE_DB_PATH']),
                'google_sheet_configured': bool(app.config['GOOGLE_SHEET_ID'])
            }
        }), 200
    except Exception as e:
        logger.error(f"❌ Erro no health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/sync', methods=['POST'])
def sincronizar_bancos():
    """Endpoint para forçar sincronização do Google Sheets para o SQLite"""
    try:
        resultado = db.forcar_sincronizacao()
        
        return jsonify({
            'success': True,
            'message': 'Sincronização concluída',
            'status': resultado
        }), 200
    except Exception as e:
        logger.error(f"❌ Erro na sincronização: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def estatisticas():
    """Endpoint para estatísticas do sistema"""
    try:
        registros = db.listar_registros()
        df_base = db.get_base_notas_data()
        
        # Estatísticas básicas
        stats = {
            'total_validacoes': len(registros),
            'total_base_notas': len(df_base),
            'ultimas_validacoes': []
        }
        
        # Últimas 10 validações
        for registro in registros[-10:]:
            stats['ultimas_validacoes'].append({
                'uf': registro.get('uf'),
                'nfe': registro.get('nfe'),
                'decisao': registro.get('decisao'),
                'data': registro.get('criado_em')
            })
        
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Iniciando aplicação na porta {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)