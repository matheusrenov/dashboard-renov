import sqlite3
import pandas as pd
from datetime import datetime

class NetworkDatabase:
    def __init__(self):
        self.db_path = 'network_data.db'
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Tabela de Redes
        c.execute('''
        CREATE TABLE IF NOT EXISTS networks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_code TEXT UNIQUE,
            network_name TEXT,
            status TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        ''')

        # Tabela de Filiais
        c.execute('''
        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_code TEXT UNIQUE,
            network_code TEXT,
            branch_name TEXT,
            status TEXT,
            city TEXT,
            state TEXT,
            region TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (network_code) REFERENCES networks (network_code)
        )
        ''')

        # Tabela de Colaboradores
        c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_code TEXT UNIQUE,
            network_code TEXT,
            branch_code TEXT,
            name TEXT,
            role TEXT,
            status TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (network_code) REFERENCES networks (network_code),
            FOREIGN KEY (branch_code) REFERENCES branches (branch_code)
        )
        ''')

        conn.commit()
        conn.close()

    def update_networks_and_branches(self, df):
        """Atualiza a base de redes e filiais"""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now()

        try:
            # Normalizar nomes das colunas
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            
            # Processar redes
            networks_df = df[['codigo_rede', 'nome_rede', 'status_rede']].drop_duplicates()
            networks_df['updated_at'] = now
            
            for _, row in networks_df.iterrows():
                conn.execute('''
                INSERT OR REPLACE INTO networks (network_code, network_name, status, updated_at)
                VALUES (?, ?, ?, ?)
                ''', (row['codigo_rede'], row['nome_rede'], row['status_rede'], now))

            # Processar filiais
            branches_df = df[[
                'codigo_filial', 'codigo_rede', 'nome_filial', 'status_filial',
                'cidade', 'estado', 'regiao'
            ]].drop_duplicates()
            
            for _, row in branches_df.iterrows():
                conn.execute('''
                INSERT OR REPLACE INTO branches (
                    branch_code, network_code, branch_name, status,
                    city, state, region, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['codigo_filial'], row['codigo_rede'], row['nome_filial'],
                    row['status_filial'], row['cidade'], row['estado'],
                    row['regiao'], now
                ))

            conn.commit()
            return True, "Base de redes e filiais atualizada com sucesso!"
        
        except Exception as e:
            conn.rollback()
            return False, f"Erro ao atualizar base: {str(e)}"
        
        finally:
            conn.close()

    def update_employees(self, df):
        """Atualiza a base de colaboradores"""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now()

        try:
            # Normalizar nomes das colunas
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            
            # Processar colaboradores
            for _, row in df.iterrows():
                conn.execute('''
                INSERT OR REPLACE INTO employees (
                    employee_code, network_code, branch_code,
                    name, role, status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['codigo_colaborador'], row['codigo_rede'],
                    row['codigo_filial'], row['nome'], row['cargo'],
                    row['status'], now
                ))

            conn.commit()
            return True, "Base de colaboradores atualizada com sucesso!"
        
        except Exception as e:
            conn.rollback()
            return False, f"Erro ao atualizar base: {str(e)}"
        
        finally:
            conn.close()

    def get_network_stats(self):
        """Retorna estatísticas das redes"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Total de redes ativas
            total_networks = conn.execute('''
                SELECT COUNT(DISTINCT network_code) 
                FROM networks 
                WHERE status = 'ATIVA'
            ''').fetchone()[0]

            # Total de filiais ativas
            total_branches = conn.execute('''
                SELECT COUNT(DISTINCT branch_code) 
                FROM branches 
                WHERE status = 'ATIVA'
            ''').fetchone()[0]

            # Total de colaboradores ativos
            total_employees = conn.execute('''
                SELECT COUNT(DISTINCT employee_code) 
                FROM employees 
                WHERE status = 'ATIVO'
            ''').fetchone()[0]

            return {
                'total_networks': total_networks,
                'total_branches': total_branches,
                'total_employees': total_employees
            }

        except Exception as e:
            print(f"Erro ao buscar estatísticas: {str(e)}")
            return {
                'total_networks': 0,
                'total_branches': 0,
                'total_employees': 0
            }
        finally:
            conn.close() 