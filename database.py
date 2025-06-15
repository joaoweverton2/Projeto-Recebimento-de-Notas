"""
Módulo de gerenciamento do banco de dados com SQLAlchemy para o sistema de notas fiscais
Versão 3.0 - Com suporte a PostgreSQL e SQLite, migração automática e persistência robusta
"""

import os
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Instâncias globais
db = SQLAlchemy()
migrate = Migrate()

class RegistroNF(db.Model):
    """Modelo SQLAlchemy para registros de notas fiscais."""
    
    __tablename__ = 'registros'
    
    id = db.Column(db.Integer, primary_key=True)
    uf = db.Column(db.String(2), nullable=False)
    nfe = db.Column(db.Integer, nullable=False)
    pedido = db.Column(db.Integer, nullable=False)
    data_recebimento = db.Column(db.String(20), nullable=False)
    valido = db.Column(db.Boolean, nullable=False)
    data_planejamento = db.Column(db.String(20), default='')
    decisao = db.Column(db.String(200), default='')
    mensagem = db.Column(db.Text, default='')
    timestamp = db.Column(db.String(30), nullable=False)
    
    def __repr__(self):
        return f'<RegistroNF {self.uf}-{self.nfe}>'
    
    def to_dict(self):
        """Converte o registro para dicionário."""
        return {
            'id': self.id,
            'uf': self.uf,
            'nfe': self.nfe,
            'pedido': self.pedido,
            'data_recebimento': self.data_recebimento,
            'valido': self.valido,
            'data_planejamento': self.data_planejamento,
            'decisao': self.decisao,
            'mensagem': self.mensagem,
            'timestamp': self.timestamp
        }

class DatabaseManager:
    """Gerenciador de banco de dados com SQLAlchemy."""
    
    def __init__(self, app: Flask = None):
        """
        Inicializa o gerenciador do banco de dados.
        
        Args:
            app: Instância da aplicação Flask
        """
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Inicializa a aplicação Flask com o banco de dados."""
        # Configuração do banco de dados
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            # Fallback para SQLite em desenvolvimento
            data_dir = Path(app.instance_path) / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            database_url = f'sqlite:///{data_dir}/registros.db'
            logger.warning("DATABASE_URL não encontrada, usando SQLite local")
        
        # Correção para PostgreSQL no Render (substitui postgres:// por postgresql://)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Inicializa extensões
        db.init_app(app)
        migrate.init_app(app, db)
        
        # Cria tabelas se necessário
        with app.app_context():
            self._create_tables_if_needed()
            self._migrate_legacy_data()
    
    def _create_tables_if_needed(self):
        """Cria as tabelas se elas não existirem."""
        try:
            db.create_all()
            logger.info("Tabelas do banco de dados verificadas/criadas")
        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {e}")
    
    def _migrate_legacy_data(self):
        """Migra dados do arquivo Excel legado para o banco de dados."""
        # Verifica se já existem dados no banco
        if RegistroNF.query.first() is not None:
            logger.info("Dados já existem no banco, pulando migração")
            return
        
        # Procura por arquivo Excel legado
        legacy_paths = [
            'data/registros.xlsx',
            'data/registros_importados.xlsx',
            Path(self.app.instance_path) / 'data' / 'registros.xlsx'
        ]
        
        legacy_path = None
        for path in legacy_paths:
            if Path(path).exists():
                legacy_path = Path(path)
                break
        
        if not legacy_path:
            logger.info("Nenhum arquivo legado encontrado para migração")
            return
        
        try:
            df = pd.read_excel(legacy_path, engine='openpyxl')
            
            # Verifica colunas obrigatórias
            required_cols = ['uf', 'nfe', 'pedido', 'data_recebimento']
            if not all(col in df.columns for col in required_cols):
                logger.error("Arquivo legado não contém colunas obrigatórias")
                return
            
            # Preenche valores padrão
            df['valido'] = df.get('valido', True)
            df['data_planejamento'] = df.get('data_planejamento', '').fillna('')
            df['decisao'] = df.get('decisao', '').fillna('')
            df['mensagem'] = df.get('mensagem', '').fillna('')
            df['timestamp'] = df.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')).fillna(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # Conversão segura de tipos
            df['nfe'] = pd.to_numeric(df['nfe'], errors='coerce').dropna().astype(int)
            df['pedido'] = pd.to_numeric(df['pedido'], errors='coerce').dropna().astype(int)
            
            # Remove linhas inválidas
            df = df.dropna(subset=required_cols)
            
            # Importa para o banco
            migrated_count = 0
            for _, row in df.iterrows():
                try:
                    registro = RegistroNF(
                        uf=str(row['uf']),
                        nfe=int(row['nfe']),
                        pedido=int(row['pedido']),
                        data_recebimento=str(row['data_recebimento']),
                        valido=bool(row['valido']),
                        data_planejamento=str(row['data_planejamento']),
                        decisao=str(row['decisao']),
                        mensagem=str(row['mensagem']),
                        timestamp=str(row['timestamp'])
                    )
                    db.session.add(registro)
                    migrated_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao migrar linha: {e}")
                    continue
            
            db.session.commit()
            logger.info(f"Dados legados migrados: {migrated_count} registros")
            
            # Renomeia arquivo para evitar re-migração
            backup_path = legacy_path.parent / f"registros_migrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            legacy_path.rename(backup_path)
            
        except Exception as e:
            logger.error(f"Falha na migração de dados legados: {e}")
            db.session.rollback()
    
    def save_verification(self, data: Dict[str, Any]) -> bool:
        """
        Salva um registro de verificação no banco de dados.
        
        Args:
            data: Dicionário contendo os dados do registro
                
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            # Validação dos campos obrigatórios
            required = ['uf', 'nfe', 'pedido', 'data_recebimento', 'valido']
            if not all(field in data for field in required):
                raise ValueError("Campos obrigatórios faltando")
            
            # Cria novo registro
            registro = RegistroNF(
                uf=str(data['uf']),
                nfe=int(data['nfe']),
                pedido=int(data['pedido']),
                data_recebimento=str(data['data_recebimento']),
                valido=bool(data['valido']),
                data_planejamento=str(data.get('data_planejamento', '')),
                decisao=str(data.get('decisao', '')),
                mensagem=str(data.get('mensagem', '')),
                timestamp=str(data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            )
            
            db.session.add(registro)
            db.session.commit()
            
            logger.info(f"Registro salvo: {registro.uf}-{registro.nfe}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar registro: {e}")
            db.session.rollback()
            return False
    
    def export_to_excel(self, output_path: str) -> bool:
        """
        Exporta os registros para um arquivo Excel.
        
        Args:
            output_path: Caminho onde o arquivo será salvo
            
        Returns:
            bool: True se a exportação foi bem-sucedida
        """
        try:
            # Busca todos os registros
            registros = RegistroNF.query.order_by(RegistroNF.timestamp.desc()).all()
            
            if not registros:
                logger.warning("Nenhum dado encontrado para exportação")
                return False
            
            # Converte para DataFrame
            data = [registro.to_dict() for registro in registros]
            df = pd.DataFrame(data)
            
            # Remove coluna ID para exportação
            if 'id' in df.columns:
                df = df.drop('id', axis=1)
            
            # Formata coluna valido
            df['valido'] = df['valido'].apply(lambda x: 'Sim' if x else 'Não')
            
            # Ordem das colunas
            col_order = [
                'uf', 'nfe', 'pedido', 'data_recebimento', 'valido',
                'data_planejamento', 'decisao', 'mensagem', 'timestamp'
            ]
            df = df[col_order]
            
            # Exporta para Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Registros')
            
            logger.info(f"Exportação realizada: {len(df)} registros em {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro na exportação: {e}")
            return False
    
    def get_record_count(self) -> int:
        """Retorna o número total de registros."""
        try:
            return RegistroNF.query.count()
        except Exception as e:
            logger.error(f"Erro ao contar registros: {e}")
            return 0
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Verifica a integridade dos dados no banco."""
        results = {
            'total_registros': 0,
            'registros_invalidos': 0,
            'problemas': [],
            'database_type': 'unknown'
        }
        
        try:
            # Identifica tipo do banco
            engine = db.engine
            results['database_type'] = engine.dialect.name
            
            # Contagem total
            results['total_registros'] = self.get_record_count()
            
            # Verifica registros com problemas
            invalid_query = RegistroNF.query.filter(
                (RegistroNF.nfe == None) | 
                (RegistroNF.pedido == None) | 
                (RegistroNF.data_recebimento == None)
            )
            results['registros_invalidos'] = invalid_query.count()
            
            if results['registros_invalidos'] > 0:
                results['problemas'].append(
                    f"{results['registros_invalidos']} registros com dados inválidos"
                )
            
            # Testa conectividade
            db.session.execute(text('SELECT 1'))
            results['conectividade'] = 'OK'
            
        except Exception as e:
            logger.error(f"Erro na validação de dados: {e}")
            results['problemas'].append(f"Erro ao validar dados: {str(e)}")
            results['conectividade'] = 'ERRO'
        
        return results
    
    def get_all_records(self) -> List[Dict[str, Any]]:
        """Retorna todos os registros como lista de dicionários."""
        try:
            registros = RegistroNF.query.order_by(RegistroNF.timestamp.desc()).all()
            return [registro.to_dict() for registro in registros]
        except Exception as e:
            logger.error(f"Erro ao buscar registros: {e}")
            return []

# Função de conveniência para compatibilidade com código existente
def create_database_manager(app: Flask) -> DatabaseManager:
    """Cria e configura o gerenciador de banco de dados."""
    return DatabaseManager(app)

# Teste da classe
if __name__ == "__main__":
    from flask import Flask
    
    print("=== TESTE DO DATABASE MANAGER COM SQLALCHEMY ===")
    
    # Cria aplicação Flask para teste
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_registros.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Cria instância do gerenciador
    db_manager = DatabaseManager(app)
    
    with app.app_context():
        # Teste de integridade
        print("\nVerificando integridade dos dados...")
        integrity = db_manager.validate_data_integrity()
        print(f"Tipo do banco: {integrity['database_type']}")
        print(f"Total de registros: {integrity['total_registros']}")
        print(f"Registros inválidos: {integrity['registros_invalidos']}")
        print(f"Conectividade: {integrity['conectividade']}")
        
        for problema in integrity['problemas']:
            print(f"Problema: {problema}")
        
        # Teste de inserção
        print("\nTestando inserção de registro...")
        test_data = {
            'uf': 'SP',
            'nfe': 123456,
            'pedido': 789012,
            'data_recebimento': '2024-01-15',
            'valido': True,
            'mensagem': 'Teste de inserção',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if db_manager.save_verification(test_data):
            print("✅ Registro inserido com sucesso!")
            print(f"Total de registros após inserção: {db_manager.get_record_count()}")
        else:
            print("❌ Falha na inserção")
        
        # Teste de exportação
        print("\nTestando exportação para Excel...")
        test_file = 'test_export_sqlalchemy.xlsx'
        
        if db_manager.export_to_excel(test_file):
            print(f"✅ Exportação realizada com sucesso! Arquivo: {test_file}")
        else:
            print("❌ Falha na exportação")
    
    print("\nTeste concluído!")

