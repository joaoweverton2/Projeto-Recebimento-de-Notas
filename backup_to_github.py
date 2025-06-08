# backup_to_github.py
import sqlite3
import pandas as pd
from datetime import datetime
import os
from git import Repo  # pip install gitpython

def backup_to_github():
    # Configurações
    db_path = 'data/registros.db'
    repo_path = 'https://github.com/joaoweverton2/Projeto-Recebimento-de-Notas'
    backup_dir = 'backups'
    
    # Criar diretório de backups se não existir
    os.makedirs(backup_dir, exist_ok=True)
    
    # Criar nome do arquivo de backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'{backup_dir}/registros_backup_{timestamp}.xlsx'
    
    # Exportar dados do SQLite para Excel
    conn = sqlite3.connect(db_path)
    df = pd.read_sql('SELECT * FROM registros', conn)
    df.to_excel(backup_file, index=False)
    conn.close()
    
    # Fazer commit e push no Git
    repo = Repo(repo_path)
    repo.git.add(backup_file)
    repo.index.commit(f'Backup de registros - {timestamp}')
    origin = repo.remote(name='origin')
    origin.push()
    
    print(f'Backup realizado e enviado para o GitHub: {backup_file}')

if __name__ == '__main__':
    backup_to_github()