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

    def validate_networks_df(self, df):
        """Valida o DataFrame de redes e filiais"""
        required_columns = {
            'codigo_rede': ['codigo_rede', 'code_rede', 'network_code'],
            'nome_rede': ['nome_rede', 'name_rede', 'network_name'],
            'status_rede': ['status_rede', 'network_status'],
            'codigo_filial': ['codigo_filial', 'code_filial', 'branch_code'],
            'nome_filial': ['nome_filial', 'name_filial', 'branch_name'],
            'status_filial': ['status_filial', 'branch_status'],
            'cidade': ['cidade', 'city'],
            'estado': ['estado', 'state'],
            'regiao': ['regiao', 'region']
        }

        # Normalizar nomes das colunas
        df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
        
        # Mapear colunas
        column_mapping = {}
        missing_columns = []
        
        for standard_name, possible_names in required_columns.items():
            found = False
            for possible_name in possible_names:
                if possible_name in df.columns:
                    column_mapping[possible_name] = standard_name
                    found = True
                    break
            if not found:
                missing_columns.append(standard_name)
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")
        
        return df.rename(columns=column_mapping)

    def validate_employees_df(self, df):
        """Valida o DataFrame de colaboradores"""
        required_columns = {
            'codigo_colaborador': ['codigo_colaborador', 'code_colaborador', 'employee_code'],
            'codigo_rede': ['codigo_rede', 'code_rede', 'network_code'],
            'codigo_filial': ['codigo_filial', 'code_filial', 'branch_code'],
            'nome': ['nome', 'name'],
            'cargo': ['cargo', 'role'],
            'status': ['status']
        }

        # Normalizar nomes das colunas
        df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
        
        # Mapear colunas
        column_mapping = {}
        missing_columns = []
        
        for standard_name, possible_names in required_columns.items():
            found = False
            for possible_name in possible_names:
                if possible_name in df.columns:
                    column_mapping[possible_name] = standard_name
                    found = True
                    break
            if not found:
                missing_columns.append(standard_name)
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")
        
        return df.rename(columns=column_mapping)

    def update_networks_and_branches(self, df):
        """Atualiza a base de redes e filiais"""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now()

        try:
            # Validar e preparar DataFrame
            df = self.validate_networks_df(df)
            
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
            # Validar e preparar DataFrame
            df = self.validate_employees_df(df)
            
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
                WHERE UPPER(status) = 'ATIVA'
            ''').fetchone()[0]

            # Total de filiais ativas
            total_branches = conn.execute('''
                SELECT COUNT(DISTINCT branch_code) 
                FROM branches 
                WHERE UPPER(status) = 'ATIVA'
            ''').fetchone()[0]

            # Total de colaboradores ativos
            total_employees = conn.execute('''
                SELECT COUNT(DISTINCT employee_code) 
                FROM employees 
                WHERE UPPER(status) = 'ATIVO'
            ''').fetchone()[0]

            return {
                'total_networks': total_networks or 0,
                'total_branches': total_branches or 0,
                'total_employees': total_employees or 0
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