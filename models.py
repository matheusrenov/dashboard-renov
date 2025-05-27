from datetime import datetime
import sqlite3
import hashlib
import os

class UserDatabase:
    def __init__(self):
        self.db_file = 'users.db'
        self._create_tables()
    
    def _create_tables(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_approved BOOLEAN DEFAULT FALSE,
            is_admin BOOLEAN DEFAULT FALSE
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username, password, email):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            hashed_password = self._hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                (username, hashed_password, email)
            )
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
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
                'is_approved': bool(user[5]),
                'is_admin': bool(user[6])
            }
        return None
    
    def approve_user(self, user_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE users SET is_approved = TRUE WHERE id = ?',
            (user_id,)
        )
        
        conn.commit()
        conn.close()
    
    def get_pending_users(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, email, created_at FROM users WHERE is_approved = FALSE')
        users = cursor.fetchall()
        
        conn.close()
        return [
            {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'created_at': user[3]
            }
            for user in users
        ]
    
    def create_admin(self, username, password, email):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            hashed_password = self._hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, password, email, is_approved, is_admin) VALUES (?, ?, ?, TRUE, TRUE)',
                (username, hashed_password, email)
            )
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close() 