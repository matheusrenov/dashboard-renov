import sqlite3
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

class NetworkDatabase:
    def __init__(self, db_path: str = 'data/networks.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Inicializa o banco de dados de redes e colaboradores."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Criar tabela de redes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                network_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Criar tabela de filiais
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS branches (
                branch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                network_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                start_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (network_id) REFERENCES networks(network_id),
                UNIQUE(network_id, name)
            )
        ''')
        
        # Criar tabela de colaboradores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                branch_id INTEGER NOT NULL,
                network_id INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                start_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
                FOREIGN KEY (network_id) REFERENCES networks(network_id),
                UNIQUE(name, branch_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def update_networks(self, df: pd.DataFrame) -> None:
        """
        Atualiza a base de redes e filiais.
        
        Args:
            df: DataFrame com dados de redes e filiais
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Processar cada rede
            for _, row in df.iterrows():
                network_name = row['nome_da_rede'].strip()
                branch_name = row['nome_da_filial'].strip()
                is_active = 1 if row['ativo'].upper() in ['ATIVO', 'ATIVA'] else 0
                start_date = pd.to_datetime(row['data_de_inicio']).strftime('%Y-%m-%d')
                
                # Inserir ou atualizar rede
                cursor.execute('''
                    INSERT INTO networks (name, is_active)
                    VALUES (?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                    is_active = excluded.is_active
                ''', (network_name, is_active))
                
                # Obter ID da rede
                cursor.execute('SELECT network_id FROM networks WHERE name = ?', (network_name,))
                network_id = cursor.fetchone()[0]
                
                # Inserir ou atualizar filial
                cursor.execute('''
                    INSERT INTO branches (network_id, name, is_active, start_date)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(network_id, name) DO UPDATE SET
                    is_active = excluded.is_active,
                    start_date = excluded.start_date
                ''', (network_id, branch_name, is_active, start_date))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        
        finally:
            conn.close()
    
    def update_employees(self, df: pd.DataFrame) -> None:
        """
        Atualiza a base de colaboradores.
        
        Args:
            df: DataFrame com dados de colaboradores
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Processar cada colaborador
            for _, row in df.iterrows():
                employee_name = row['colaborador'].strip()
                network_name = row['rede'].strip()
                branch_name = row['filial'].strip()
                is_active = 1 if row['ativo'].upper() in ['ATIVO', 'ATIVA'] else 0
                start_date = pd.to_datetime(row['data_de_cadastro']).strftime('%Y-%m-%d')
                
                # Obter IDs da rede e filial
                cursor.execute('''
                    SELECT n.network_id, b.branch_id
                    FROM networks n
                    JOIN branches b ON b.network_id = n.network_id
                    WHERE n.name = ? AND b.name = ?
                ''', (network_name, branch_name))
                
                result = cursor.fetchone()
                if not result:
                    raise ValueError(f"Rede/Filial não encontrada: {network_name}/{branch_name}")
                
                network_id, branch_id = result
                
                # Inserir ou atualizar colaborador
                cursor.execute('''
                    INSERT INTO employees (name, branch_id, network_id, is_active, start_date)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name, branch_id) DO UPDATE SET
                    is_active = excluded.is_active,
                    start_date = excluded.start_date
                ''', (employee_name, branch_id, network_id, is_active, start_date))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        
        finally:
            conn.close()
    
    def get_valid_networks(self) -> List[str]:
        """
        Retorna lista de redes válidas.
        
        Returns:
            Lista com nomes das redes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM networks WHERE is_active = 1')
        networks = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return networks
    
    def get_valid_branches(self) -> List[str]:
        """
        Retorna lista de filiais válidas.
        
        Returns:
            Lista com nomes das filiais
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM branches WHERE is_active = 1')
        branches = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return branches
    
    def get_network_metrics(self) -> List[Dict[str, Any]]:
        """
        Retorna métricas por rede.
        
        Returns:
            Lista de dicionários com métricas por rede
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                n.name as network_name,
                COUNT(DISTINCT b.branch_id) as total_branches,
                COUNT(DISTINCT e.employee_id) as total_employees,
                SUM(CASE WHEN e.is_active = 1 THEN 1 ELSE 0 END) as active_employees
            FROM networks n
            LEFT JOIN branches b ON b.network_id = n.network_id
            LEFT JOIN employees e ON e.network_id = n.network_id
            WHERE n.is_active = 1
            GROUP BY n.network_id
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'network': row[0],
                'total_branches': row[1],
                'total_employees': row[2],
                'active_employees': row[3]
            }
            for row in results
        ] 