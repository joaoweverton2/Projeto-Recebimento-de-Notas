from flask import Flask, request, jsonify, send_file, send_from_directory
from pathlib import Path
import os
from datetime import datetime
import logging
from database import DatabaseManager
from validacao_nfe import ValidadorNFE
from io import BytesIO
import pandas as pd
import time

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

# ============================================================
# ROTAS DA API - PRINCIPAIS
# ============================================================

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
        
        # Tenta salvar o registro com retry
        max_retries = 3
        for tentativa in range(max_retries):
            try:
                db.criar_registro(registro)
                logger.info(f"✅ Registro salvo: {registro['decisao']}")
                break
            except Exception as e:
                if tentativa < max_retries - 1:
                    logger.warning(f"Tentativa {tentativa + 1} falhou ao salvar registro. Tentando novamente...")
                    time.sleep(2)
                else:
                    logger.error(f"❌ Erro ao salvar registro após {max_retries} tentativas: {str(e)}")

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

# ============================================================
# ROTAS DE DIAGNÓSTICO E MONITORAMENTO
# ============================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar saúde do sistema e consistência dos bancos"""
    try:
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

@app.route('/health/detalhado', methods=['GET'])
def health_detalhado():
    """Endpoint para health check detalhado com informações de performance"""
    try:
        # Mede tempo de resposta do Google Sheets
        start_time = time.time()
        db_status = db.verificar_saude_banco()
        sheets_response_time = time.time() - start_time
        
        # Mede tempo de resposta do SQLite
        start_time = time.time()
        df_sqlite = db.get_base_notas_data()
        sqlite_response_time = time.time() - start_time
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'performance': {
                'google_sheets_response_time': round(sheets_response_time, 3),
                'sqlite_response_time': round(sqlite_response_time, 3)
            },
            'database': db_status,
            'registros': {
                'total_validacoes': len(db.listar_registros()),
                'total_base_notas': len(df_sqlite)
            },
            'config': {
                'sqlite_path': str(app.config['SQLITE_DB_PATH']),
                'google_sheet_configured': bool(app.config['GOOGLE_SHEET_ID']),
                'planilha_base': db.NOME_PLANILHA_BASE,
                'planilha_registros': db.NOME_PLANILHA_REGISTROS
            }
        }), 200
    except Exception as e:
        logger.error(f"❌ Erro no health detalhado: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/sync', methods=['GET', 'POST'])
def sincronizar_bancos():
    """Endpoint para forçar sincronização do Google Sheets para o SQLite"""
    try:
        resultado = db.forcar_sincronizacao()
        return jsonify({
            'success': resultado.get('success', False),
            'message': resultado.get('message', ''),
            'status': resultado
        }), 200 if resultado.get('success') else 500
    except Exception as e:
        logger.error(f"❌ Erro na sincronização: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/limpar-cache', methods=['POST'])
def limpar_cache():
    """Endpoint para limpar e recarregar o cache SQLite do Google Sheets"""
    try:
        resultado = db.limpar_cache_registros()
        return jsonify(resultado), 200 if resultado.get('success') else 500
    except Exception as e:
        logger.error(f"❌ Erro ao limpar cache: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/diagnostico-registros', methods=['GET'])
def diagnostico_registros():
    """Endpoint para diagnosticar problemas na worksheet registros_nf"""
    try:
        status = db.verificar_registros_nf()
        
        # Testa escrita na worksheet (opcional)
        test_result = None
        if status.get('existe', False):
            try:
                registro_teste = {
                    'uf': 'TESTE',
                    'nfe': 999999,
                    'pedido': 999999,
                    'data_recebimento': datetime.now().strftime('%Y-%m-%d'),
                    'data_planejamento': 'TESTE',
                    'decisao': 'TESTE_SISTEMA',
                    'criado_em': datetime.now().isoformat()
                }
                resultado = db.criar_registro(registro_teste)
                test_result = {
                    'success': True,
                    'message': 'Teste de escrita realizado com sucesso',
                    'registro_teste': resultado
                }
            except Exception as e:
                test_result = {
                    'success': False,
                    'error': str(e)
                }
        
        return jsonify({
            'diagnostico': status,
            'teste_escrita': test_result,
            'recomendacao': 'Sistema funcionando corretamente' if status.get('existe') else 'Verifique as permissões da planilha'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no diagnóstico: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/diagnostico-completo', methods=['GET'])
def diagnostico_completo():
    """Endpoint para diagnóstico completo do sistema"""
    try:
        resultado = db.get_diagnostico_completo()
        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"❌ Erro no diagnóstico completo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def estatisticas():
    """Endpoint para estatísticas do sistema"""
    try:
        registros = db.listar_registros()
        df_base = db.get_base_notas_data()
        
        stats = {
            'total_validacoes': len(registros),
            'total_base_notas': len(df_base),
            'ultimas_validacoes': []
        }
        
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

@app.route('/api-endpoints', methods=['GET'])
def listar_endpoints():
    """Lista todos os endpoints disponíveis na API"""
    endpoints = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            endpoints.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
    
    return jsonify({
        'total_endpoints': len(endpoints),
        'endpoints': endpoints,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/testar-registro', methods=['POST'])
def testar_registro():
    """Endpoint para testar criação de registro manualmente"""
    try:
        registro_teste = {
            'uf': request.json.get('uf', 'SP'),
            'nfe': int(request.json.get('nfe', 123456)),
            'pedido': int(request.json.get('pedido', 789012)),
            'data_recebimento': request.json.get('data_recebimento', datetime.now().strftime('%Y-%m-%d')),
            'data_planejamento': request.json.get('data_planejamento', '2025/Dezembro'),
            'decisao': request.json.get('decisao', 'TESTE_MANUAL')
        }
        
        resultado = db.criar_registro(registro_teste)
        
        return jsonify({
            'success': True,
            'registro': resultado,
            'mensagem': 'Registro de teste criado com sucesso no Google Sheets'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Iniciando aplicação na porta {port} (debug={debug})")
    logger.info("📋 Endpoints disponíveis:")
    logger.info("   - GET  /")
    logger.info("   - GET  /admin")
    logger.info("   - POST /verificar")
    logger.info("   - POST /atualizar-base")
    logger.info("   - GET  /download-registros")
    logger.info("   - GET  /health")
    logger.info("   - GET  /health/detalhado")
    logger.info("   - GET/POST /sync")
    logger.info("   - POST /limpar-cache")
    logger.info("   - GET  /diagnostico-registros")
    logger.info("   - GET  /diagnostico-completo")
    logger.info("   - GET  /stats")
    logger.info("   - GET  /api-endpoints")
    logger.info("   - POST /testar-registro")
    
    app.run(host='0.0.0.0', port=port, debug=debug)