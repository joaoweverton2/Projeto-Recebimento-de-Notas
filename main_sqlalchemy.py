"""
Aplicação principal para o Sistema de Verificação de Notas Fiscais
Versão 3.0 - Com suporte a PostgreSQL e SQLite via SQLAlchemy
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import pytz
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Importa o novo gerenciador de banco de dados
from database_sqlalchemy import DatabaseManager, db, migrate

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

# VERIFICAÇÃO DO ARQUIVO DE NOTAS
print("\n" + "="*50)
print(f"📂 Diretório base: {BASE_DIR}")
print(f"📝 Arquivo de notas: {app.config['BASE_NOTAS']}")
print(f"🔍 Arquivo existe? {app.config['BASE_NOTAS'].exists()}")
print(f"🗄️ Banco de dados: {os.getenv('DATABASE_URL', 'SQLite local')}")
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
        
        # Se a validação for bem-sucedida, salvar o registro no banco
        if resultado.get('valido', False):
            # Adicionar timestamp ao registro
            resultado['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Salva usando o novo gerenciador
            success = db_manager.save_verification(resultado)
            
            if not success:
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
        # Exportar para Excel temporário
        temp_excel = app.config['DATABASE_FOLDER'] / 'registros_exportados.xlsx'
        
        # Exporta os dados usando o novo gerenciador
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

@app.route('/check-db')
def check_db():
    """Rota para verificar o status do banco de dados."""
    try:
        integrity = db_manager.validate_data_integrity()
        
        return jsonify({
            'total_registros': integrity['total_registros'],
            'database_type': integrity['database_type'],
            'conectividade': integrity['conectividade'],
            'registros_invalidos': integrity['registros_invalidos'],
            'problemas': integrity['problemas'],
            'database_url': os.getenv('DATABASE_URL', 'SQLite local'),
            'status': 'OK' if integrity['conectividade'] == 'OK' else 'ERROR'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'ERROR'
        })

@app.route('/init-db')
def init_db():
    """Rota para inicializar/verificar o banco de dados."""
    try:
        with app.app_context():
            # Força criação das tabelas
            db.create_all()
            
            # Verifica integridade
            integrity = db_manager.validate_data_integrity()
            
            return jsonify({
                'success': True,
                'message': f'Banco de dados inicializado/verificado',
                'total_registros': integrity['total_registros'],
                'database_type': integrity['database_type'],
                'conectividade': integrity['conectividade']
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao inicializar banco: {str(e)}'
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

@app.route('/admin')
def admin():
    """Rota para a página de administração."""
    return render_template('admin.html')

@app.route('/api/registros')
def api_registros():
    """API para listar todos os registros."""
    try:
        registros = db_manager.get_all_records()
        return jsonify({
            'success': True,
            'data': registros,
            'total': len(registros)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Comando CLI para migrações
@app.cli.command()
def init_db_cli():
    """Inicializa o banco de dados via CLI."""
    try:
        db.create_all()
        print("✅ Banco de dados inicializado com sucesso!")
        
        integrity = db_manager.validate_data_integrity()
        print(f"📊 Total de registros: {integrity['total_registros']}")
        print(f"🗄️ Tipo do banco: {integrity['database_type']}")
        
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")

@app.cli.command()
def migrate_legacy():
    """Migra dados legados via CLI."""
    try:
        db_manager._migrate_legacy_data()
        print("✅ Migração de dados legados concluída!")
    except Exception as e:
        print(f"❌ Erro na migração: {e}")

if __name__ == '__main__':
    # DEBUG EXTRA - Mostra estrutura de arquivos
    print("\nESTRUTURA DE ARQUIVOS:")
    for root, dirs, files in os.walk(BASE_DIR):
        level = root.replace(str(BASE_DIR), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files[:5]:  # Limita a 5 arquivos por diretório
            print(f"{subindent}{file}")
        if len(files) > 5:
            print(f"{subindent}... e mais {len(files) - 5} arquivos")
    
    # Verifica conectividade do banco
    with app.app_context():
        try:
            integrity = db_manager.validate_data_integrity()
            print(f"\n🗄️ BANCO DE DADOS:")
            print(f"   Tipo: {integrity['database_type']}")
            print(f"   Conectividade: {integrity['conectividade']}")
            print(f"   Registros: {integrity['total_registros']}")
            if integrity['problemas']:
                print(f"   Problemas: {', '.join(integrity['problemas'])}")
        except Exception as e:
            print(f"\n❌ ERRO NO BANCO: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

