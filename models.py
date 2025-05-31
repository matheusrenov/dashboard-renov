from datetime import datetime
import sqlite3
import hashlib
import os

class UserDatabase:
    """Classe simples para gerenciar usuários"""
    
    def __init__(self):
        pass
    
    def authenticate(self, username, password):
        """Autenticação simples"""
        return username == 'admin' and password == 'admin'
    
    def get_user_info(self, username):
        """Retorna informações do usuário"""
        if username == 'admin':
            return {'username': 'admin', 'is_admin': True}
        return None

class ImportHistory:
    """Classe para gerenciar o histórico de importações usando SQLite"""
    
    def __init__(self):
        self.db_file = 'data/dashboard.db'
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Garante que a tabela existe no banco de dados"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS import_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_type VARCHAR(50) NOT NULL,
            filename VARCHAR(255),
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            imported_by INTEGER,
            row_count INTEGER,
            FOREIGN KEY (imported_by) REFERENCES user(id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_import(self, import_type: str, filename: str, imported_by: int, row_count: int):
        """Adiciona um novo registro de importação"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO import_history (import_type, filename, imported_by, row_count)
        VALUES (?, ?, ?, ?)
        ''', (import_type, filename, imported_by, row_count))
        
        conn.commit()
        conn.close()
    
    def get_last_imports(self, limit: int = 2) -> list:
        """Retorna as últimas importações"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT import_type, filename, import_date, imported_by, row_count
        FROM import_history
        ORDER BY import_date DESC
        LIMIT ?
        ''', (limit,))
        
        imports = cursor.fetchall()
        conn.close()
        
        return [
            {
                'import_type': imp[0],
                'filename': imp[1],
                'import_date': datetime.strptime(imp[2], '%Y-%m-%d %H:%M:%S'),
                'imported_by': imp[3],
                'row_count': imp[4]
            }
            for imp in imports
        ] 