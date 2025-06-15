"""
Módulo de gerenciamento do banco de dados com SQLAlchemy para o sistema de notas fiscais
Versão 4.3 - Com tratamento robusto de formatos de data
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, Any
import logging
import locale

import pandas as pd
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import exc, text, func

# Configura locale para parsing de meses em português
locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database.log')
    ]
)
logger = logging.getLogger(__name__)

# Instâncias globais do SQLAlchemy e Migrate
db = SQLAlchemy()
migrate = Migrate()

class RegistroNF(db.Model):
    """Modelo SQLAlchemy para registros de notas fiscais."""
    
    __tablename__ = 'registros_nf'
    
    id = db.Column(db.Integer, primary_key=True)
    uf = db.Column(db.String(6), nullable=False)
    nfe = db.Column(db.BigInteger, nullable=False)
    pedido = db.Column(db.BigInteger, nullable=False)
    data_recebimento = db.Column(db.Date, nullable=False)
    valido = db.Column(db.Boolean, nullable=False, default=True)
    data_planejamento = db.Column(db.Date, nullable=True)
    decisao = db.Column(db.String(200), nullable=True)
    mensagem = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('uf', 'nfe', name='uq_uf_nfe'),
    )
    
    def __repr__(self):
        return f'<RegistroNF {self.uf}-{self.nfe} (Pedido: {self.pedido})>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o registro para dicionário."""
        return {
            'id': self.id,
            'uf': self.uf,
            'nfe': self.nfe,
            'pedido': self.pedido,
            'data_recebimento': self.data_recebimento.isoformat(),
            'valido': self.valido,
            'data_planejamento': self.data_planejamento.isoformat() if self.data_planejamento else None,
            'decisao': self.decisao,
            'mensagem': self.mensagem,
            'criado_em': self.criado_em.isoformat(),
            'atualizado_em': self.atualizado_em.isoformat()
        }

class RegistroNFInput(TypedDict):
    """Tipo para entrada de dados de nota fiscal."""
    uf: str
    nfe: int
    pedido: int
    data_recebimento: str
    valido: Optional[bool]
    data_planejamento: Optional[str]
    decisao: Optional[str]
    mensagem: Optional[str]

class DatabaseManager:
    """Gerenciador de banco de dados com operações CRUD para notas fiscais."""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Configura e inicializa a extensão do banco de dados."""
        database_url = self._get_database_url(app)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        migrate.init_app(app, db)
        
        self._register_cli_commands(app)
        
        with app.app_context():
            self._initialize_database()
    
    def _parse_date(self, date_str: str) -> datetime.date:
        """
        Converte uma string de data em objeto date, com tratamento de vários formatos.
        Suporta:
        - YYYY-MM-DD
        - YYYY/MM/DD
        - YYYY-MM
        - YYYY/MM
        - YYYY/MMMM (português)
        - YYYY-MM-DDTHH:MM:SS (ISO com tempo)
        """
        if not date_str or not isinstance(date_str, str):
            return datetime.now().date()
            
        date_str = date_str.strip().upper()
        
        # Remove time part if exists
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        
        formats_to_try = [
            '%Y-%m-%d',    # ISO format
            '%Y/%m/%d',     # Slash format
            '%Y-%m',        # Year-month only
            '%Y/%m',       # Year/month only
            '%Y/%B',       # Year/month name (portuguese)
            '%d/%m/%Y',     # Brazilian format
            '%m/%d/%Y',     # US format
        ]
        
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_str, fmt)
                # For formats without day, use first day of month
                if fmt in ['%Y-%m', '%Y/%m', '%Y/%B']:
                    return dt.date().replace(day=1)
                return dt.date()
            except ValueError:
                continue
        
        logger.warning(f"Formato de data não reconhecido: {date_str}. Usando data atual.")
        return datetime.now().date()
    
    def _get_database_url(self, app: Flask) -> str:
        """Obtém a URL do banco de dados com fallback para SQLite."""
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            data_dir = Path(app.instance_path) / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            database_url = f'sqlite:///{data_dir}/registros.db'
            logger.warning("DATABASE_URL não encontrada, usando SQLite local")
        
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        return database_url
    
    def _register_cli_commands(self, app: Flask) -> None:
        """Registra comandos CLI para gerenciamento do banco."""
        @app.cli.command('db-reset')
        def reset_db():
            """Reseta o banco de dados (apaga e recria todas as tabelas)"""
            try:
                db.drop_all()
                db.create_all()
                logger.info("Banco de dados resetado com sucesso")
                print("✅ Banco de dados resetado com sucesso!")
            except Exception as e:
                logger.error(f"Falha ao resetar banco: {str(e)}")
                print(f"❌ Erro ao resetar banco: {e}")
        
        @app.cli.command('db-init')
        def init_db():
            """Inicializa o banco de dados (cria tabelas se não existirem)"""
            try:
                db.create_all()
                logger.info("Banco de dados inicializado com sucesso")
                print("✅ Banco de dados inicializado com sucesso!")
            except Exception as e:
                logger.error(f"Falha ao inicializar banco: {str(e)}")
                print(f"❌ Erro ao inicializar banco: {e}")
        
        @app.cli.command('db-clean-duplicates')
        def clean_duplicates():
            """Remove registros duplicados do banco de dados."""
            try:
                subquery = db.session.query(
                    RegistroNF.uf,
                    RegistroNF.nfe,
                    func.min(RegistroNF.id).label('min_id')
                ).group_by(RegistroNF.uf, RegistroNF.nfe).subquery()
                
                deleted = db.session.query(RegistroNF).filter(
                    RegistroNF.id.notin_(db.session.query(subquery.c.min_id))
                ).delete(synchronize_session=False)
                
                db.session.commit()
                logger.info(f"Removidos {deleted} registros duplicados")
                print(f"✅ Removidos {deleted} registros duplicados!")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Falha ao remover duplicatas: {str(e)}")
                print(f"❌ Erro ao remover duplicatas: {e}")
    
    def _initialize_database(self) -> None:
        """Inicializa o banco de dados e migra dados legados se necessário."""
        try:
            if not self._tables_exist():
                db.create_all()
                logger.info("Tabelas criadas com sucesso")
                self._migrate_legacy_data()
        except exc.SQLAlchemyError as e:
            logger.error(f"Falha ao inicializar banco de dados: {str(e)}")
            raise
    
    def _tables_exist(self) -> bool:
        """Verifica se as tabelas já existem no banco de dados."""
        inspector = db.inspect(db.engine)
        return inspector.has_table(RegistroNF.__tablename__)
    
    def _migrate_legacy_data(self) -> int:
        """Migra dados de arquivos Excel legados para o banco de dados."""
        if RegistroNF.query.limit(1).first() is not None:
            logger.info("Banco já contém dados, pulando migração")
            return 0
        
        legacy_path = self._find_legacy_file()
        if not legacy_path:
            logger.info("Nenhum arquivo legado encontrado para migração")
            return 0
        
        try:
            df = pd.read_excel(legacy_path, engine='openpyxl')
            df = self._remove_duplicates(df)
            return self._import_dataframe(df)
        except Exception as e:
            logger.error(f"Falha na migração de dados legados: {str(e)}")
            return 0
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove registros duplicados do DataFrame antes da importação."""
        if not all(col in df.columns for col in ['uf', 'nfe']):
            return df
        
        df['uf'] = df['uf'].astype(str).str.strip().str.upper().str[:6]
        df['nfe'] = pd.to_numeric(df['nfe'], errors='coerce')
        df = df.dropna(subset=['nfe'])
        
        df_duplicates = df.duplicated(subset=['uf', 'nfe'], keep='first')
        if df_duplicates.any():
            logger.warning(f"Removendo {df_duplicates.sum()} registros duplicados do arquivo")
            df = df[~df_duplicates]
        
        return df
    
    def _find_legacy_file(self) -> Optional[Path]:
        """Procura por arquivos legados em locais conhecidos."""
        possible_locations = [
            Path('data/registros.xlsx'),
            Path('data/registros_importados.xlsx'),
            Path(self.app.instance_path) / 'data' / 'registros.xlsx'
        ]
        
        for path in possible_locations:
            if path.exists():
                return path
        return None
    
    def _import_dataframe(self, df: pd.DataFrame) -> int:
        """Importa dados de um DataFrame para o banco de dados com tratamento de erros."""
        required_cols = ['uf', 'nfe', 'pedido', 'data_recebimento']
        if not all(col in df.columns for col in required_cols):
            logger.error("DataFrame não contém colunas obrigatórias")
            return 0
        
        df = self._preprocess_dataframe(df)
        existing_pairs = self._get_existing_pairs()
        imported_count = 0
        batch_size = 50
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            try:
                for _, row in batch.iterrows():
                    uf = str(row['uf'])
                    nfe = int(row['nfe'])
                    
                    if (uf, nfe) in existing_pairs:
                        logger.debug(f"Registro duplicado ignorado: {uf}-{nfe}")
                        continue
                        
                    try:
                        registro = self._create_registro_from_row(row)
                        db.session.add(registro)
                        imported_count += 1
                        existing_pairs.add((uf, nfe))
                    except exc.IntegrityError:
                        db.session.rollback()
                        logger.warning(f"Registro duplicado (concorrência): {uf}-{nfe}")
                        continue
                
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro no lote {i//batch_size}: {str(e)}")
        
        logger.info(f"Dados migrados com sucesso: {imported_count}/{len(df)} registros")
        return imported_count
    
    def _get_existing_pairs(self) -> set:
        """Retorna conjunto de pares (UF, NFe) já existentes no banco."""
        existing_pairs = set()
        try:
            records = db.session.query(RegistroNF.uf, RegistroNF.nfe).all()
            existing_pairs = {(str(r.uf), int(r.nfe)) for r in records}
        except Exception as e:
            logger.error(f"Erro ao verificar registros existentes: {str(e)}")
        return existing_pairs
    
    def _preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Realiza pré-processamento no DataFrame antes da importação."""
        df['valido'] = df.get('valido', True)
        df['data_planejamento'] = df.get('data_planejamento', '').fillna('')
        df['decisao'] = df.get('decisao', '').fillna('')
        df['mensagem'] = df.get('mensagem', '').fillna('')
        
        df['uf'] = df['uf'].str.upper().str[:6]
        df['nfe'] = pd.to_numeric(df['nfe'], errors='coerce').dropna().astype('int64')
        df['pedido'] = pd.to_numeric(df['pedido'], errors='coerce').dropna().astype('int64')
        
        # Convert dates using our robust parser
        df['data_recebimento'] = df['data_recebimento'].apply(
            lambda x: self._parse_date(str(x)) if pd.notna(x) else datetime.now().date()
        )
        df['data_planejamento'] = df['data_planejamento'].apply(
            lambda x: self._parse_date(str(x)) if pd.notna(x) else None
        )
        
        df = df.dropna(subset=['uf', 'nfe', 'pedido', 'data_recebimento'])
        
        return df
    
    def _create_registro_from_row(self, row: pd.Series) -> RegistroNF:
        """Cria um objeto RegistroNF a partir de uma linha do DataFrame."""
        return RegistroNF(
            uf=str(row['uf']),
            nfe=int(row['nfe']),
            pedido=int(row['pedido']),
            data_recebimento=row['data_recebimento'],
            valido=bool(row['valido']),
            data_planejamento=row['data_planejamento'] if pd.notna(row['data_planejamento']) else None,
            decisao=str(row['decisao']) if pd.notna(row['decisao']) else None,
            mensagem=str(row['mensagem']) if pd.notna(row['mensagem']) else None
        )
    
    def criar_registro(self, data: RegistroNFInput) -> Optional[RegistroNF]:
        """Cria um novo registro de nota fiscal no banco de dados."""
        try:
            registro = RegistroNF(
                uf=data['uf'].upper()[:6],
                nfe=data['nfe'],
                pedido=data['pedido'],
                data_recebimento=self._parse_date(data['data_recebimento']),
                valido=data.get('valido', True),
                data_planejamento=self._parse_date(data['data_planejamento']) if data.get('data_planejamento') else None,
                decisao=data.get('decisao'),
                mensagem=data.get('mensagem')
            )
            
            db.session.add(registro)
            db.session.commit()
            logger.info(f"Registro criado: {registro}")
            return registro
        except exc.IntegrityError:
            db.session.rollback()
            logger.warning(f"Registro já existe: {data['uf']}-{data['nfe']}")
            return None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Falha ao criar registro: {str(e)}")
            return None
    
    def obter_registro(self, registro_id: int) -> Optional[RegistroNF]:
        """Obtém um registro pelo ID."""
        return RegistroNF.query.get(registro_id)
    
    def obter_registro_por_nfe(self, uf: str, nfe: int) -> Optional[RegistroNF]:
        """Obtém um registro pela combinação UF + NFe."""
        return RegistroNF.query.filter_by(uf=uf.upper(), nfe=nfe).first()
    
    def atualizar_registro(self, registro_id: int, data: Dict[str, Any]) -> Optional[RegistroNF]:
        """Atualiza um registro existente."""
        try:
            registro = RegistroNF.query.get(registro_id)
            if not registro:
                return None
                
            if 'uf' in data:
                registro.uf = data['uf'].upper()[:6]
            if 'nfe' in data:
                registro.nfe = data['nfe']
            if 'pedido' in data:
                registro.pedido = data['pedido']
            if 'data_recebimento' in data:
                registro.data_recebimento = self._parse_date(data['data_recebimento'])
            if 'valido' in data:
                registro.valido = data['valido']
            if 'data_planejamento' in data:
                registro.data_planejamento = self._parse_date(data['data_planejamento']) if data.get('data_planejamento') else None
            if 'decisao' in data:
                registro.decisao = data['decisao']
            if 'mensagem' in data:
                registro.mensagem = data['mensagem']
            
            db.session.commit()
            logger.info(f"Registro atualizado: {registro}")
            return registro
        except Exception as e:
            db.session.rollback()
            logger.error(f"Falha ao atualizar registro {registro_id}: {str(e)}")
            return None
    
    def remover_registro(self, registro_id: int) -> bool:
        """Remove um registro do banco de dados."""
        try:
            registro = RegistroNF.query.get(registro_id)
            if registro:
                db.session.delete(registro)
                db.session.commit()
                logger.info(f"Registro removido: {registro}")
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Falha ao remover registro {registro_id}: {str(e)}")
            return False
    
    def listar_registros(self, filtros: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[RegistroNF]:
        """Lista registros com filtros opcionais."""
        query = RegistroNF.query
        
        if filtros:
            for key, value in filtros.items():
                if hasattr(RegistroNF, key):
                    if value is None:
                        query = query.filter(getattr(RegistroNF, key).is_(None))
                    else:
                        query = query.filter(getattr(RegistroNF, key) == value)
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def exportar_para_excel(self, filepath: str) -> bool:
        """Exporta todos os registros para um arquivo Excel."""
        try:
            registros = self.listar_registros()
            data = [r.to_dict() for r in registros]
            
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            logger.info(f"Dados exportados para {filepath}")
            return True
        except Exception as e:
            logger.error(f"Falha ao exportar dados: {str(e)}")
            return False

# Testes
if __name__ == "__main__":
    from flask import Flask
    
    print("=== TESTE DO DATABASE MANAGER (TRATAMENTO DE DATAS) ===")
    
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    db_manager = DatabaseManager(app)
    
    with app.app_context():
        # Criar tabelas
        db.create_all()
        
        # Teste com diferentes formatos de data
        test_cases = [
            {'format': 'YYYY-MM-DD', 'date': '2024-01-15'},
            {'format': 'YYYY/MM/DD', 'date': '2024/01/15'},
            {'format': 'YYYY-MM', 'date': '2024-01'},
            {'format': 'YYYY/MM', 'date': '2024/01'},
            {'format': 'YYYY/MMMM (pt)', 'date': '2024/FEVEREIRO'},
            {'format': 'DD/MM/YYYY', 'date': '15/01/2024'},
            {'format': 'ISO com tempo', 'date': '2024-01-15T12:00:00'},
        ]
        
        for i, test_case in enumerate(test_cases):
            test_data = {
                'uf': f'SP{i}',
                'nfe': 1000 + i,
                'pedido': 2000 + i,
                'data_recebimento': test_case['date'],
                'valido': True,
                'mensagem': f'Teste de formato: {test_case["format"]}'
            }
            
            registro = db_manager.criar_registro(test_data)
            if registro:
                print(f"✅ {test_case['format']}: {registro.data_recebimento}")
            else:
                print(f"❌ Falha com formato {test_case['format']}")
    
    print("\nTeste concluído!")