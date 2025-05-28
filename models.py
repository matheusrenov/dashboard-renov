from datetime import datetime
import sqlite3
import hashlib
import os

class UserDatabase:
    def __init__(self):
        self.db_file = 'data/users.db'
        self.super_admin_email = 'matheus@renovsmart.com.br'
        self._create_tables()
        self._create_initial_users()
    
    def _create_tables(self):
        # Garante que o diretório data existe
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Recria a tabela com estrutura simplificada
        cursor.execute('DROP TABLE IF EXISTS users')
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_super_admin BOOLEAN DEFAULT FALSE
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _create_initial_users(self):
        """Cria apenas os dois usuários principais"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Limpa usuários existentes
            cursor.execute('DELETE FROM users')
            
            # Cria os dois usuários principais
            hashed_password = self._hash_password('admin123')
            
            # Criar admin padrão
            cursor.execute(
                'INSERT INTO users (username, password, email, is_super_admin) VALUES (?, ?, ?, ?)',
                ('admin', hashed_password, 'admin@renov.com.br', False)
            )
            
            # Criar super admin
            cursor.execute(
                'INSERT INTO users (username, password, email, is_super_admin) VALUES (?, ?, ?, ?)',
                ('matheus', hashed_password, self.super_admin_email, True)
            )
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Erro ao criar usuários iniciais: {str(e)}")
    
    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_user(self, username, password):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        hashed_password = self._hash_password(password)
        cursor.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, hashed_password)
        )
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'email': user[3],
                'is_super_admin': bool(user[5])
            }
        return None

    def test_connection(self):
        """Testa a conexão com o banco de dados"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.fetchone()
            conn.close()
            return True
        except Exception as e:
            raise Exception(f"Erro na conexão com o banco de dados: {str(e)}") 