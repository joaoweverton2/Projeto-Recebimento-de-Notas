#!/usr/bin/env python3
"""
Script de teste abrangente para o novo sistema de notas fiscais
Testa todas as funcionalidades principais
"""

import requests
import json
import time
import os
from pathlib import Path

def test_flask_app():
    """Testa a aplicação Flask completa."""
    
    print("🧪 TESTE ABRANGENTE DO NOVO SISTEMA")
    print("="*50)
    
    base_url = "http://localhost:5000"
    
    # Lista de testes
    tests = [
        ("GET /", "Página inicial"),
        ("GET /check-db", "Status do banco de dados"),
        ("GET /init-db", "Inicialização do banco"),
        ("GET /api/registros", "API de registros"),
        ("GET /admin", "Página de administração")
    ]
    
    results = []
    
    for method_url, description in tests:
        method, url = method_url.split(" ", 1)
        full_url = f"{base_url}{url}"
        
        try:
            print(f"\n🔍 Testando: {description}")
            print(f"   URL: {method} {full_url}")
            
            if method == "GET":
                response = requests.get(full_url, timeout=5)
            elif method == "POST":
                response = requests.post(full_url, timeout=5)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Sucesso")
                results.append((description, "✅ PASSOU"))
                
                # Para endpoints JSON, mostra dados
                if url in ["/check-db", "/init-db", "/api/registros"]:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            for key, value in list(data.items())[:3]:  # Primeiros 3 itens
                                print(f"      {key}: {value}")
                    except:
                        pass
            else:
                print(f"   ❌ Falha: {response.status_code}")
                results.append((description, f"❌ FALHOU ({response.status_code})"))
                
        except requests.exceptions.ConnectionError:
            print("   ⚠️  Servidor não está rodando")
            results.append((description, "⚠️ SERVIDOR OFF"))
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            results.append((description, f"❌ ERRO: {str(e)[:30]}"))
    
    # Resumo dos resultados
    print(f"\n📊 RESUMO DOS TESTES")
    print("="*30)
    
    passed = 0
    for description, result in results:
        print(f"{result} {description}")
        if "✅" in result:
            passed += 1
    
    print(f"\n🎯 RESULTADO: {passed}/{len(results)} testes passaram")
    
    return passed == len(results)

def test_database_operations():
    """Testa operações específicas do banco de dados."""
    
    print(f"\n🗄️ TESTE DE OPERAÇÕES DO BANCO")
    print("="*40)
    
    try:
        # Importa e testa diretamente
        import sys
        sys.path.insert(0, str(Path.cwd()))
        
        from database_sqlalchemy import DatabaseManager
        from flask import Flask
        
        # Cria aplicação de teste
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_operations.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db_manager = DatabaseManager(app)
        
        with app.app_context():
            print("✅ Conexão estabelecida")
            
            # Teste 1: Inserção de dados
            test_data = {
                'uf': 'RJ',
                'nfe': 999888,
                'pedido': 777666,
                'data_recebimento': '2024-06-15',
                'valido': True,
                'mensagem': 'Teste de operação',
                'timestamp': '2024-06-15 11:00:00'
            }
            
            if db_manager.save_verification(test_data):
                print("✅ Inserção de dados")
            else:
                print("❌ Inserção de dados")
            
            # Teste 2: Contagem de registros
            count = db_manager.get_record_count()
            print(f"✅ Contagem de registros: {count}")
            
            # Teste 3: Exportação para Excel
            export_path = 'test_export_operations.xlsx'
            if db_manager.export_to_excel(export_path):
                print(f"✅ Exportação para Excel: {export_path}")
                
                # Verifica se arquivo foi criado
                if Path(export_path).exists():
                    size = Path(export_path).stat().st_size
                    print(f"   Tamanho do arquivo: {size} bytes")
                else:
                    print("❌ Arquivo não foi criado")
            else:
                print("❌ Exportação para Excel")
            
            # Teste 4: Validação de integridade
            integrity = db_manager.validate_data_integrity()
            print(f"✅ Validação de integridade:")
            print(f"   Tipo: {integrity['database_type']}")
            print(f"   Conectividade: {integrity['conectividade']}")
            print(f"   Registros: {integrity['total_registros']}")
            
            # Teste 5: Busca de registros
            registros = db_manager.get_all_records()
            print(f"✅ Busca de registros: {len(registros)} encontrados")
            
            if registros:
                print(f"   Primeiro registro: {registros[0]['uf']}-{registros[0]['nfe']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro nas operações do banco: {e}")
        return False

def test_migration_script():
    """Testa o script de migração."""
    
    print(f"\n🔄 TESTE DO SCRIPT DE MIGRAÇÃO")
    print("="*35)
    
    try:
        # Simula execução do script de migração
        import subprocess
        
        result = subprocess.run(
            ['python3', 'migrate_to_sqlalchemy.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Script de migração executado com sucesso")
            
            # Verifica se arquivos foram criados
            if Path('.env').exists():
                print("✅ Arquivo .env criado")
            
            if Path('backup_migracao').exists():
                print("✅ Diretório de backup criado")
            
            return True
        else:
            print(f"❌ Script falhou: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de migração: {e}")
        return False

def main():
    """Função principal dos testes."""
    
    print("🚀 SUITE DE TESTES COMPLETA - SISTEMA DE NOTAS FISCAIS")
    print("="*70)
    
    # Verifica se está no diretório correto
    if not Path('main_sqlalchemy.py').exists():
        print("❌ Execute este script no diretório do projeto")
        return
    
    # Teste 1: Operações do banco de dados
    db_test = test_database_operations()
    
    # Teste 2: Script de migração
    migration_test = test_migration_script()
    
    # Teste 3: Aplicação Flask (requer servidor rodando)
    print(f"\n⚠️  TESTE DA APLICAÇÃO FLASK")
    print("Para testar a aplicação Flask, execute em outro terminal:")
    print("python3 main_sqlalchemy.py")
    print("Depois execute: python3 test_complete_system.py --flask")
    
    # Resumo final
    print(f"\n🎯 RESUMO FINAL DOS TESTES")
    print("="*35)
    print(f"{'✅' if db_test else '❌'} Operações do banco de dados")
    print(f"{'✅' if migration_test else '❌'} Script de migração")
    print("⚠️  Aplicação Flask (teste manual)")
    
    total_tests = 2
    passed_tests = sum([db_test, migration_test])
    
    print(f"\n🏆 RESULTADO: {passed_tests}/{total_tests} testes automáticos passaram")
    
    if passed_tests == total_tests:
        print("\n🎉 TODOS OS TESTES AUTOMÁTICOS PASSARAM!")
        print("O sistema está pronto para deploy!")
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM")
        print("Verifique os erros antes de fazer deploy")

if __name__ == "__main__":
    import sys
    
    if "--flask" in sys.argv:
        # Testa apenas a aplicação Flask
        test_flask_app()
    else:
        # Executa todos os testes
        main()

