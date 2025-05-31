import sqlite3
import hashlib
import os
from typing import Optional, Dict, Any

class UserDatabase:
    def __init__(self, db_path: str = 'data/users.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Inicializa o banco de dados de usuários."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Criar tabela de usuários se não existir
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inserir usuários padrão se não existirem
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            # Senha: admin123
            admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute(
                'INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                ('admin', admin_pass, 1)
            )
            cursor.execute(
                'INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                ('matheus', admin_pass, 1)
            )
        
        conn.commit()
        conn.close()
    
    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verifica as credenciais do usuário.
        
        Args:
            username: Nome de usuário
            password: Senha em texto plano
        
        Returns:
            Dict com dados do usuário se autenticado, None caso contrário
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        hashed_pass = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute(
            'SELECT username, is_admin, is_active FROM users WHERE username = ? AND password = ?',
            (username, hashed_pass)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'username': result[0],
                'is_admin': bool(result[1]),
                'is_active': bool(result[2])
            }
        return None
    
    def add_user(self, username: str, password: str, is_admin: bool = False) -> bool:
        """
        Adiciona um novo usuário.
        
        Args:
            username: Nome de usuário
            password: Senha em texto plano
            is_admin: Se o usuário é administrador
        
        Returns:
            True se usuário foi adicionado com sucesso
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            hashed_pass = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute(
                'INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                (username, hashed_pass, int(is_admin))
            )
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.IntegrityError:
            return False
    
    def update_password(self, username: str, new_password: str) -> bool:
        """
        Atualiza a senha do usuário.
        
        Args:
            username: Nome de usuário
            new_password: Nova senha em texto plano
        
        Returns:
            True se senha foi atualizada com sucesso
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        hashed_pass = hashlib.sha256(new_password.encode()).hexdigest()
        
        cursor.execute(
            'UPDATE users SET password = ? WHERE username = ?',
            (hashed_pass, username)
        )
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def delete_user(self, username: str) -> bool:
        """
        Remove um usuário.
        
        Args:
            username: Nome de usuário a ser removido
        
        Returns:
            True se usuário foi removido com sucesso
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_all_users(self) -> list:
        """
        Retorna todos os usuários.
        
        Returns:
            Lista de dicionários com dados dos usuários
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT username, is_admin, is_active, created_at FROM users')
        users = cursor.fetchall()
        
        conn.close()
        
        return [
            {
                'username': user[0],
                'is_admin': bool(user[1]),
                'is_active': bool(user[2]),
                'created_at': user[3]
            }
            for user in users
        ] 