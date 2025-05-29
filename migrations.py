import sqlite3
import os

def init_db():
    # Garantir que o diretório data existe
    os.makedirs('data', exist_ok=True)
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('data/dashboard.db')
    cursor = conn.cursor()
    
    # Criar tabela de histórico de importações
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
    print("Banco de dados inicializado com sucesso!")

if __name__ == '__main__':
    init_db() 