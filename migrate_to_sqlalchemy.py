#!/usr/bin/env python3
"""
Script de migração do sistema de notas fiscais
Migra do SQLite atual para PostgreSQL com SQLAlchemy
"""

import os
import sys
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

def migrate_from_sqlite_to_new_system():
    """Migra dados do SQLite atual para o novo sistema."""
    
    print("🔄 INICIANDO MIGRAÇÃO DO SISTEMA DE NOTAS FISCAIS")
    print("="*60)
    
    # Caminhos dos arquivos
    old_db_path = Path('data/registros.db')
    old_excel_path = Path('data/registros.xlsx')
    backup_dir = Path('backup_migracao')
    
    # Cria diretório de backup
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print(f"📁 Diretório de backup: {backup_dir}")
    print(f"⏰ Timestamp da migração: {timestamp}")
    
    # Lista para armazenar todos os dados
    all_data = []
    
    # 1. Migra dados do SQLite se existir
    if old_db_path.exists():
        print(f"\n📊 Migrando dados do SQLite: {old_db_path}")
        try:
            conn = sqlite3.connect(old_db_path)
            df_sqlite = pd.read_sql_query("SELECT * FROM registros", conn)
            conn.close()
            
            print(f"   ✅ {len(df_sqlite)} registros encontrados no SQLite")
            all_data.append(df_sqlite)
            
            # Backup do SQLite
            backup_sqlite = backup_dir / f'registros_sqlite_{timestamp}.db'
            old_db_path.rename(backup_sqlite)
            print(f"   💾 Backup criado: {backup_sqlite}")
            
        except Exception as e:
            print(f"   ❌ Erro ao migrar SQLite: {e}")
    
    # 2. Migra dados do Excel se existir
    if old_excel_path.exists():
        print(f"\n📈 Migrando dados do Excel: {old_excel_path}")
        try:
            df_excel = pd.read_excel(old_excel_path, engine='openpyxl')
            print(f"   ✅ {len(df_excel)} registros encontrados no Excel")
            all_data.append(df_excel)
            
            # Backup do Excel
            backup_excel = backup_dir / f'registros_excel_{timestamp}.xlsx'
            old_excel_path.rename(backup_excel)
            print(f"   💾 Backup criado: {backup_excel}")
            
        except Exception as e:
            print(f"   ❌ Erro ao migrar Excel: {e}")
    
    # 3. Consolida todos os dados
    if all_data:
        print(f"\n🔗 Consolidando dados de {len(all_data)} fontes...")
        
        # Combina todos os DataFrames
        df_combined = pd.concat(all_data, ignore_index=True)
        
        # Remove duplicatas baseado em uf, nfe, pedido
        df_combined = df_combined.drop_duplicates(
            subset=['uf', 'nfe', 'pedido'], 
            keep='last'
        )
        
        print(f"   ✅ {len(df_combined)} registros únicos após consolidação")
        
        # Salva dados consolidados para o novo sistema
        consolidated_path = Path('data/registros_consolidados.xlsx')
        df_combined.to_excel(consolidated_path, index=False, engine='openpyxl')
        print(f"   💾 Dados consolidados salvos: {consolidated_path}")
        
        return len(df_combined)
    
    else:
        print("\n⚠️  Nenhum dado encontrado para migração")
        return 0

def setup_new_system():
    """Configura o novo sistema com SQLAlchemy."""
    
    print(f"\n🔧 CONFIGURANDO NOVO SISTEMA")
    print("="*40)
    
    # Verifica se as dependências estão instaladas
    try:
        import flask_sqlalchemy
        import flask_migrate
        import psycopg2
        print("✅ Dependências do SQLAlchemy instaladas")
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("💡 Execute: pip install -r requirements_new.txt")
        return False
    
    # Verifica configuração do banco
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        print(f"✅ DATABASE_URL configurada: {database_url[:50]}...")
    else:
        print("⚠️  DATABASE_URL não configurada, usando SQLite local")
    
    # Cria arquivo .env se não existir
    env_file = Path('.env')
    if not env_file.exists():
        print("📝 Criando arquivo .env...")
        with open(env_file, 'w') as f:
            f.write("# Configurações do Sistema de Notas Fiscais\n")
            f.write("FLASK_ENV=development\n")
            f.write("FLASK_DEBUG=True\n")
            if not database_url:
                f.write("DATABASE_URL=sqlite:///data/registros.db\n")
            f.write("SECRET_KEY=sua_chave_secreta_aqui\n")
        print(f"   ✅ Arquivo .env criado: {env_file}")
    
    return True

def test_new_system():
    """Testa o novo sistema."""
    
    print(f"\n🧪 TESTANDO NOVO SISTEMA")
    print("="*30)
    
    try:
        # Importa o novo sistema
        sys.path.insert(0, str(Path.cwd()))
        from database_sqlalchemy import DatabaseManager
        from flask import Flask
        
        # Cria aplicação de teste
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///data/registros.db')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Testa o gerenciador
        db_manager = DatabaseManager(app)
        
        with app.app_context():
            # Verifica integridade
            integrity = db_manager.validate_data_integrity()
            
            print(f"✅ Tipo do banco: {integrity['database_type']}")
            print(f"✅ Conectividade: {integrity['conectividade']}")
            print(f"✅ Total de registros: {integrity['total_registros']}")
            
            if integrity['problemas']:
                for problema in integrity['problemas']:
                    print(f"⚠️  {problema}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def main():
    """Função principal do script de migração."""
    
    print("🚀 SCRIPT DE MIGRAÇÃO - SISTEMA DE NOTAS FISCAIS")
    print("="*70)
    print("Este script migra do sistema atual para SQLAlchemy + PostgreSQL")
    print()
    
    # Verifica se está no diretório correto
    if not Path('main.py').exists():
        print("❌ Execute este script no diretório raiz do projeto")
        return
    
    # Passo 1: Migração de dados
    print("PASSO 1: Migração de dados existentes")
    migrated_count = migrate_from_sqlite_to_new_system()
    
    # Passo 2: Configuração do novo sistema
    print("\nPASSO 2: Configuração do novo sistema")
    if not setup_new_system():
        print("❌ Falha na configuração do novo sistema")
        return
    
    # Passo 3: Teste do novo sistema
    print("\nPASSO 3: Teste do novo sistema")
    if test_new_system():
        print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"📊 {migrated_count} registros migrados")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Substitua 'main.py' por 'main_sqlalchemy.py'")
        print("2. Substitua 'database.py' por 'database_sqlalchemy.py'")
        print("3. Atualize 'requirements.txt' com 'requirements_new.txt'")
        print("4. Configure DATABASE_URL para PostgreSQL no Render")
        print("5. Faça deploy da nova versão")
    else:
        print("\n❌ FALHA NO TESTE DO NOVO SISTEMA")
        print("Verifique os erros acima antes de prosseguir")

if __name__ == "__main__":
    main()

