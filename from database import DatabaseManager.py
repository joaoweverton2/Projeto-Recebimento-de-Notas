from database import DatabaseManager
from pprint import pprint

db_manager = DatabaseManager()

print("=== REGISTROS NO BANCO DE DADOS ===50")
registros = db_manager.get_all_records()
pprint(registros)

print(f"\nTotal de registros: {len(registros)}")