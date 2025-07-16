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
from database import DatabaseManager
load_dotenv()

# Configurações da aplicação
app = Flask(__name__)

# Configurações básicas
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

# Configurações de diretórios
app.config["UPLOAD_FOLDER"] = BASE_DIR / "uploads"
app.config["DATABASE_FOLDER"] = BASE_DIR / "data"
app.config["BASE_NOTAS"] = BASE_DIR / "data" / "Base_de_notas.xlsx"

# Configurar timezone padrão
app.config["TIMEZONE"] = pytz.timezone("America/Sao_Paulo")

# Garantir que os diretórios existam
app.config["UPLOAD_FOLDER"].mkdir(exist_ok=True)
app.config["DATABASE_FOLDER"].mkdir(exist_ok=True)

# Inicializa o gerenciador de banco de dados
db_manager = DatabaseManager(app)

# Importação do módulo de validação
from validacao_nfe import processar_validacao

@app.route("/")
def index():
    """Rota principal que renderiza a página inicial."""
    return render_template("index.html")

@app.route("/verificar", methods=["POST"])
def verificar():
    """
    Processa a requisição de verificação de nota fiscal.
    """
    try:
        # Obter dados do formulário
        uf = request.form.get("uf", "").strip().upper()
        nfe = request.form.get("nfe", "").strip()
        pedido = request.form.get("pedido", "").strip()
        data_recebimento_str = request.form.get("data_recebimento", "").strip()
        
        # Processar a validação
        resultado = processar_validacao(
            uf, nfe, pedido, 
            data_recebimento_str,
            app.config["BASE_NOTAS"]
        )
        
        # Se a validação for bem-sucedida, salvar o registro no banco
        if resultado.get("valido", False):
            registro_data = {
                "uf": uf,
                "nfe": int(nfe),
                "pedido": int(pedido),
                "data_recebimento": data_recebimento_str,
                "valido": resultado["valido"],
                "data_planejamento": resultado.get("data_planejamento", ""),
                "decisao": resultado.get("decisao", ""),
                "mensagem": resultado.get("mensagem", "")
            }
            
            registro = db_manager.criar_registro(registro_data)
            
            if not registro:
                resultado["mensagem"] += " (Aviso: Erro ao salvar no banco de dados)"
            
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({
            "valido": False,
            "mensagem": f"Erro durante o processamento: {str(e)}"
        })

@app.route("/download/registros", methods=["GET"])
def download_registros():
    """Baixa os registros em formato Excel."""
    try:
        temp_excel = app.config["DATABASE_FOLDER"] / "registros_exportados.xlsx"
        
        if db_manager.exportar_para_excel(str(temp_excel)):
            return send_file(
                str(temp_excel),
                as_attachment=True,
                download_name="registros_notas_fiscais.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            return jsonify({
                "sucesso": False,
                "mensagem": "Falha ao gerar arquivo Excel"
            })
    except Exception as e:
        return jsonify({
            "sucesso": False,
            "mensagem": f"Erro ao baixar o arquivo: {str(e)}"
        })
@app.route("/check-db")
def check_db():
    """Rota para verificar o status do Google Sheets."""
    try:
        # Tenta listar registros para verificar a conexão com o Google Sheets
        total_registros = len(db_manager.listar_registros())
        
        return jsonify({
            "total_registros": total_registros,
            "database_type": "Google Sheets",
            "google_sheet_id": os.getenv("GOOGLE_SHEET_ID", "Não configurado"),
            "status": "OK"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "ERROR"
        })

@app.route("/atualizar-base", methods=["POST"])
def atualizar_base():
    """Atualiza a base de dados de notas fiscais."""
    try:
        if "arquivo" not in request.files:
            return jsonify({
                "sucesso": False,
                "mensagem": "Nenhum arquivo enviado"
            })
        
        arquivo = request.files["arquivo"]
        
        if arquivo.filename == "":
            return jsonify({
                "sucesso": False,
                "mensagem": "Nenhum arquivo selecionado"
            })
        
        if not arquivo.filename.endswith((".xlsx", ".xls")):
            return jsonify({
                "sucesso": False,
                "mensagem": "O arquivo deve ser um Excel (.xlsx ou .xls)"
            })
        
        # Salva o arquivo Base_de_notas.xlsx
        filename = secure_filename("Base_de_notas.xlsx")
        arquivo.save(app.config["BASE_NOTAS"])
        
        # Força a atualização do cache/reload da aplicação se necessário
        # Isso garante que as próximas validações usem o arquivo atualizado
        print(f'📝 Base de notas atualizada: {app.config["BASE_NOTAS"]}')
        print(f'📊 Arquivo existe: {app.config["BASE_NOTAS"].exists()}')
        
        # Verifica se o arquivo foi salvo corretamente
        if not app.config["BASE_NOTAS"].exists():
            return jsonify({
                "sucesso": False,
                "mensagem": "Erro ao salvar o arquivo no servidor"
            })
        
        return jsonify({
            "sucesso": True,
            "mensagem": "Base de dados atualizada com sucesso. As próximas validações usarão os novos dados."
        })
    
    except Exception as e:
        return jsonify({
            "sucesso": False,
            "mensagem": f"Erro ao atualizar a base de dados: {str(e)}"
        })

@app.route("/admin")
def admin():
    """Rota para a página de administração."""
    return render_template("admin.html")

@app.route("/api/registros")
def api_registros():
    """API para listar todos os registros."""
    try:

        registros_dict = db_manager.listar_registros()
        return jsonify({
            "success": True,
            "data": registros_dict,
            "total": len(registros_dict)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


