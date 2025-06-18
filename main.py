"""
Aplicação principal para o Sistema de Verificação de Notas Fiscais
Versão 4.1 - Compatível com database.py atualizado
"""

import os
import sys
from datetime import datetime, timedelta
import pytz
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text  # Importação adicionada para corrigir o erro

# Carrega variáveis de ambiente
load_dotenv()

# Importa o gerenciador de banco de dados
from database import DatabaseManager, db, migrate, RegistroNF  # Adicionado RegistroNF na importação

# Configurações da aplicação
app = Flask(__name__)

# Configurações básicas
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

# Configurações de diretórios
app.config['UPLOAD_FOLDER'] = BASE_DIR / 'uploads'
app.config['DATABASE_FOLDER'] = BASE_DIR / 'data'
app.config['BASE_NOTAS'] = BASE_DIR / 'data' / 'Base_de_notas.xlsx'

# Configurar timezone padrão
app.config['TIMEZONE'] = pytz.timezone('America/Sao_Paulo')

# Garantir que os diretórios existam
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['DATABASE_FOLDER'].mkdir(exist_ok=True)

# Inicializa o gerenciador de banco de dados
db_manager = DatabaseManager(app)

# VERIFICAÇÃO DO ARQUIVO DE NOTAS E MIGRAÇÃO FORÇADA
print("\n" + "="*50)
print(f"📂 Diretório base: {BASE_DIR}")
print(f"📝 Arquivo de notas: {app.config['BASE_NOTAS']}")
print(f"🔍 Arquivo existe? {app.config['BASE_NOTAS'].exists()}")
print(f"🗄️ Banco de dados: {os.getenv('DATABASE_URL', 'SQLite local')}")

# Verifica se há dados no banco e força migração se necessário
with app.app_context():
    try:
        # Para PostgreSQL, verificamos a conexão primeiro
        database_url = os.getenv('DATABASE_URL', 'SQLite local')
        if 'postgresql' in database_url or 'postgres' in database_url:
            print("🐘 Usando PostgreSQL")
        else:
            print("🗄️ Usando SQLite local")
            
        # Tenta contar registros
        count = RegistroNF.query.count()
        print(f"📊 Registros no banco: {count}")
        
        if count == 0:
            print("🔄 Banco vazio, tentando migração automática...")
            imported = db_manager._migrate_legacy_data()
            print(f"✅ Migração concluída: {imported} registros importados")
            
            # Verifica novamente após a migração
            final_count = RegistroNF.query.count()
            print(f"📊 Total final de registros: {final_count}")
        else:
            print("✅ Banco já contém dados")
            
    except Exception as e:
        print(f"⚠️ Erro na verificação inicial: {str(e)}")
        print("🔄 Tentando migração de emergência...")
        
        # Em caso de erro, tenta criar tabelas e migrar
        try:
            db.create_all()
            print("✅ Tabelas criadas/verificadas")
            
            # Tenta migração direta
            imported = db_manager._migrate_legacy_data()
            print(f"✅ Migração de emergência concluída: {imported} registros")
            
        except Exception as e2:
            print(f"❌ Erro na migração de emergência: {str(e2)}")
            print("💡 Execute manualmente: python migrate_data.py")

print("="*50 + "\n")

# Importação do módulo de validação
from validacao_nfe import processar_validacao

@app.route('/')
def index():
    """Rota principal que renderiza a página inicial."""
    return render_template('index.html')

@app.route('/verificar', methods=['POST'])
def verificar():
    """
    Processa a requisição de verificação de nota fiscal.
    """
    try:
        # Obter dados do formulário
        uf = request.form.get('uf', '').strip().upper()
        nfe = request.form.get('nfe', '').strip()
        pedido = request.form.get('pedido', '').strip()
        data_recebimento_str = request.form.get('data_recebimento', '').strip()
        
        # Processar a validação
        resultado = processar_validacao(
            uf, nfe, pedido, 
            data_recebimento_str,
            app.config['BASE_NOTAS']
        )
        
        # Se a validação for bem-sucedida, salvar o registro no banco
        if resultado.get('valido', False):
            registro_data = {
                'uf': uf,
                'nfe': int(nfe),
                'pedido': int(pedido),
                'data_recebimento': data_recebimento_str,
                'valido': resultado['valido'],
                'data_planejamento': resultado.get('data_planejamento', ''),
                'decisao': resultado.get('decisao', ''),
                'mensagem': resultado.get('mensagem', '')
            }
            
            registro = db_manager.criar_registro(registro_data)
            
            if not registro:
                resultado['mensagem'] += ' (Aviso: Erro ao salvar no banco de dados)'
            
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({
            'valido': False,
            'mensagem': f'Erro durante o processamento: {str(e)}'
        })

@app.route('/download/registros', methods=['GET'])
def download_registros():
    """Baixa os registros em formato Excel."""
    try:
        temp_excel = app.config['DATABASE_FOLDER'] / 'registros_exportados.xlsx'
        
        if db_manager.exportar_para_excel(str(temp_excel)):
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

@app.route('/check-db')
def check_db():
    """Rota para verificar o status do banco de dados."""
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))  # Agora usando text importado corretamente
            conectividade = "OK"
        
        total_registros = db.session.query(RegistroNF).count()
        
        return jsonify({
            'total_registros': total_registros,
            'database_type': str(db.engine.url),
            'conectividade': conectividade,
            'database_url': os.getenv('DATABASE_URL', 'SQLite local'),
            'status': 'OK'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'ERROR'
        })

@app.route('/atualizar-base', methods=['POST'])
def atualizar_base():
    """Atualiza a base de dados de notas fiscais."""
    try:
        if 'arquivo' not in request.files:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum arquivo enviado'
            })
        
        arquivo = request.files['arquivo']
        
        if arquivo.filename == '':
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum arquivo selecionado'
            })
        
        if not arquivo.filename.endswith(('.xlsx', '.xls')):
            return jsonify({
                'sucesso': False,
                'mensagem': 'O arquivo deve ser um Excel (.xlsx ou .xls)'
            })
        
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

@app.route('/admin')
def admin():
    """Rota para a página de administração."""
    return render_template('admin.html')

@app.route('/api/registros')
def api_registros():
    """API para listar todos os registros."""
    try:
        registros = db_manager.listar_registros()
        registros_dict = [r.to_dict() for r in registros]
        return jsonify({
            'success': True,
            'data': registros_dict,
            'total': len(registros_dict)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    # DEBUG EXTRA - Mostra estrutura de arquivos
    print("\nESTRUTURA DE ARQUIVOS:")
    for root, dirs, files in os.walk(BASE_DIR):
        level = root.replace(str(BASE_DIR), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files[:5]:
            print(f"{subindent}{file}")
        if len(files) > 5:
            print(f"{subindent}... e mais {len(files) - 5} arquivos")
    
    # Verifica conectividade do banco
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("\n🗄️ BANCO DE DADOS:")
                print(f"   Tipo: {db.engine.url}")
                print("   Conectividade: OK")
                print(f"   Registros: {db.session.query(RegistroNF).count()}")
        except Exception as e:
            print(f"\n❌ ERRO NO BANCO: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)