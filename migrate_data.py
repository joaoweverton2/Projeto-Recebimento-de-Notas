"""
Script de migração de dados iniciais - VERSÃO SIMPLIFICADA PARA POSTGRESQL
Este script força o carregamento dos dados iniciais no primeiro deploy
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório do projeto ao path
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

from flask import Flask
from database import DatabaseManager, db, RegistroNF
import logging

# Configuração de logging mais simples
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def force_migration():
    """Força a migração de dados iniciais para PostgreSQL."""
    app = Flask(__name__)
    
    # Configuração do banco PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada! Para PostgreSQL, esta variável é obrigatória.")
        return
    
    # Corrige URL do PostgreSQL se necessário
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    print(f"🐘 Conectando ao PostgreSQL...")
    print(f"🔗 URL: {database_url[:50]}...")
    
    # Inicializa apenas o SQLAlchemy, sem o DatabaseManager para evitar loops
    db.init_app(app)
    
    with app.app_context():
        try:
            # Cria as tabelas se não existirem (para casos onde Flask-Migrate falhou)
            db.create_all()
            print("✅ Tabelas verificadas/criadas")
            
            # Verifica quantos registros existem
            count = RegistroNF.query.count()
            print(f"📊 Registros existentes: {count}")
            
            if count == 0:
                print("🔄 Banco vazio, iniciando migração...")
                
                # Procura o arquivo de dados
                data_file = project_dir / 'data' / 'registros.xlsx'
                if not data_file.exists():
                    print(f"❌ Arquivo não encontrado: {data_file}")
                    return
                
                print(f"📁 Arquivo encontrado: {data_file}")
                
                # Carrega e processa os dados
                import pandas as pd
                df = pd.read_excel(data_file, engine='openpyxl')
                print(f"📋 Carregados {len(df)} registros do Excel")
                
                # Remove duplicatas
                df = df.drop_duplicates(subset=['uf', 'nfe'], keep='first')
                print(f"📋 Após remoção de duplicatas: {len(df)} registros")
                
                # Importa os dados
                imported = 0
                for _, row in df.iterrows():
                    try:
                        # Processa a data de recebimento
                        data_recebimento = row['data_recebimento']
                        if isinstance(data_recebimento, str):
                            # Trata formatos como "2025/MAIO"
                            if '/' in data_recebimento and any(mes in data_recebimento.upper() for mes in ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']):
                                # Converte mês em português para número
                                meses = {
                                    'JANEIRO': '01', 'FEVEREIRO': '02', 'MARÇO': '03', 'ABRIL': '04',
                                    'MAIO': '05', 'JUNHO': '06', 'JULHO': '07', 'AGOSTO': '08',
                                    'SETEMBRO': '09', 'OUTUBRO': '10', 'NOVEMBRO': '11', 'DEZEMBRO': '12'
                                }
                                parts = data_recebimento.split('/')
                                if len(parts) == 2:
                                    ano = parts[0]
                                    mes_nome = parts[1].upper()
                                    if mes_nome in meses:
                                        data_recebimento = f"{ano}-{meses[mes_nome]}-01"
                        
                        data_recebimento = pd.to_datetime(data_recebimento).date()
                        
                        # Processa a data de planejamento
                        data_planejamento = None
                        if pd.notna(row.get('data_planejamento')):
                            try:
                                data_planejamento_raw = row['data_planejamento']
                                if isinstance(data_planejamento_raw, str) and '/' in data_planejamento_raw:
                                    # Mesmo tratamento para data de planejamento
                                    meses = {
                                        'JANEIRO': '01', 'FEVEREIRO': '02', 'MARÇO': '03', 'ABRIL': '04',
                                        'MAIO': '05', 'JUNHO': '06', 'JULHO': '07', 'AGOSTO': '08',
                                        'SETEMBRO': '09', 'OUTUBRO': '10', 'NOVEMBRO': '11', 'DEZEMBRO': '12'
                                    }
                                    parts = data_planejamento_raw.split('/')
                                    if len(parts) == 2:
                                        ano = parts[0]
                                        mes_nome = parts[1].upper()
                                        if mes_nome in meses:
                                            data_planejamento_raw = f"{ano}-{meses[mes_nome]}-01"
                                
                                data_planejamento = pd.to_datetime(data_planejamento_raw).date()
                            except:
                                data_planejamento = None
                        
                        registro = RegistroNF(
                            uf=str(row['uf']).upper()[:6],
                            nfe=int(row['nfe']),
                            pedido=int(row['pedido']),
                            data_recebimento=data_recebimento,
                            valido=bool(row.get('valido', True)),
                            data_planejamento=data_planejamento,
                            decisao=str(row.get('decisao', '')) if pd.notna(row.get('decisao')) else None,
                            mensagem=str(row.get('mensagem', '')) if pd.notna(row.get('mensagem')) else None
                        )
                        db.session.add(registro)
                        imported += 1
                    except Exception as e:
                        print(f"⚠️ Erro ao processar registro {row.get('nfe', 'N/A')}: {e}")
                        continue
                
                # Salva no banco
                db.session.commit()
                print(f"✅ Migração concluída: {imported} registros importados")
                
                # Verifica o resultado final
                final_count = RegistroNF.query.count()
                print(f"📊 Total final no banco: {final_count}")
                
            else:
                print("✅ Banco já contém dados, migração não necessária")
                
        except Exception as e:
            print(f"❌ Erro durante a migração: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    force_migration()

