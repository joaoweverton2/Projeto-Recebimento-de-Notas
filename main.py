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

# Carrega variáveis de ambiente
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
app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
app.config["DATABASE_FOLDER"].mkdir(parents=True, exist_ok=True)

# Inicializa o gerenciador de banco de dados
db_manager = DatabaseManager(app)

# Importação do módulo de validação (após inicialização do app)
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
        
        # Validação básica dos campos
        if not all([uf, nfe, pedido, data_recebimento_str]):
            return jsonify({
                "valido": False,
                "mensagem": "Todos os campos são obrigatórios"
            })
        
        try:
            nfe = int(nfe)
            pedido = int(pedido)
        except ValueError:
            return jsonify({
                "valido": False,
                "mensagem": "NFe e Pedido devem ser números"
            })
        
        # Processar a validação
        resultado = processar_validacao(
            uf=uf, 
            nfe=nfe, 
            pedido=pedido, 
            data_recebimento_str=data_recebimento_str,
            caminho_base_notas=app.config["BASE_NOTAS"]
        )
        
        # Se a validação for bem-sucedida, salvar o registro no banco
        if resultado.get("valido", False):
            registro_data = {
                "uf": uf,
                "nfe": nfe,
                "pedido": pedido,
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
        app.logger.error(f"Erro em /verificar: {str(e)}", exc_info=True)
        return jsonify({
            "valido": False,
            "mensagem": f"Erro durante o processamento: {str(e)}"
        }), 500

@app.route("/download/registros", methods=["GET"])
def download_registros():
    """Baixa os registros em formato Excel."""
    try:
        temp_excel = app.config["DATABASE_FOLDER"] / "registros_exportados.xlsx"
        
        if db_manager.exportar_para_excel(str(temp_excel)):
            return send_file(
                str(temp_excel),
                as_attachment=True,
                download_name=f"registros_notas_fiscais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        return jsonify({
            "sucesso": False,
            "mensagem": "Falha ao gerar arquivo Excel"
        }), 500
        
    except Exception as e:
        app.logger.error(f"Erro em /download/registros: {str(e)}", exc_info=True)
        return jsonify({
            "sucesso": False,
            "mensagem": f"Erro ao baixar o arquivo: {str(e)}"
        }), 500

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
        app.logger.error(f"Erro em /check-db: {str(e)}", exc_info=True)
        return jsonify({
            "error": str(e),
            "status": "ERROR"
        }), 500

@app.route("/atualizar-base", methods=["POST"])
def atualizar_base():
    """Atualiza a base de dados de notas fiscais."""
    try:
        if "arquivo" not in request.files:
            return jsonify({
                "sucesso": False,
                "mensagem": "Nenhum arquivo enviado"
            }), 400
        
        arquivo = request.files["arquivo"]
        
        if arquivo.filename == "":
            return jsonify({
                "sucesso": False,
                "mensagem": "Nenhum arquivo selecionado"
            }), 400
        
        if not arquivo.filename.lower().endswith((".xlsx", ".xls")):
            return jsonify({
                "sucesso": False,
                "mensagem": "O arquivo deve ser um Excel (.xlsx ou .xls)"
            }), 400
        
        # Garante que o diretório existe
        app.config["DATABASE_FOLDER"].mkdir(parents=True, exist_ok=True)
        
        # Salva o arquivo Base_de_notas.xlsx
        filename = secure_filename("Base_de_notas.xlsx")
        arquivo.save(app.config["BASE_NOTAS"])
        
        # Log de atualização
        app.logger.info(f"Base de notas atualizada: {app.config['BASE_NOTAS']}")
        app.logger.info(f"Tamanho do arquivo: {os.path.getsize(app.config['BASE_NOTAS'])} bytes")
        
        # Verifica se o arquivo foi salvo corretamente
        if not app.config["BASE_NOTAS"].exists():
            return jsonify({
                "sucesso": False,
                "mensagem": "Erro ao salvar o arquivo no servidor"
            }), 500
        
        return jsonify({
            "sucesso": True,
            "mensagem": "Base de dados atualizada com sucesso. As próximas validações usarão os novos dados."
        })
    
    except Exception as e:
        app.logger.error(f"Erro em /atualizar-base: {str(e)}", exc_info=True)
        return jsonify({
            "sucesso": False,
            "mensagem": f"Erro ao atualizar a base de dados: {str(e)}"
        }), 500

@app.route("/admin")
def admin():
    """Rota para a página de administração."""
    return render_template("admin.html")

@app.route("/api/registros")
def api_registros():
    """API para listar todos os registros."""
    try:
        registros = db_manager.listar_registros()
        return jsonify({
            "success": True,
            "data": registros,
            "total": len(registros)
        })
    except Exception as e:
        app.logger.error(f"Erro em /api/registros: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)


