import sqlite3
import pandas as pd
from datetime import datetime

class NetworkDatabase:
    def __init__(self):
        self.db_path = 'network_data.db'
        self.init_db()

    def init_db(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Remover tabelas existentes para garantir estrutura atualizada
        c.execute('DROP TABLE IF EXISTS employees')
        c.execute('DROP TABLE IF EXISTS networks_branches')

        # Tabela de Redes e Filiais - Usando apenas TEXT para datas
        c.execute('''
        CREATE TABLE IF NOT EXISTS networks_branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_rede TEXT NOT NULL,
            nome_filial TEXT NOT NULL,
            ativo TEXT DEFAULT 'ATIVO',
            data_inicio TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(nome_rede, nome_filial)
        )
        ''')

        # Tabela de Colaboradores - Usando apenas TEXT para datas
        c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador TEXT NOT NULL,
            filial TEXT NOT NULL,
            rede TEXT NOT NULL,
            ativo TEXT DEFAULT 'ATIVO',
            data_cadastro TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (filial, rede) REFERENCES networks_branches(nome_filial, nome_rede)
        )
        ''')

        conn.commit()
        conn.close()

    def format_date(self, date_str):
        """Formata a data para o formato YYYY-MM-DD"""
        if not date_str:
            return None
        try:
            # Tenta converter para datetime e depois para string no formato desejado
            return pd.to_datetime(date_str).strftime('%Y-%m-%d')
        except:
            return date_str

    def validate_networks_df(self, df):
        """Valida o DataFrame de redes e filiais"""
        required_columns = {
            'nome_rede': ['Nome da Rede'],
            'nome_filial': ['Nome da Filial'],
            'ativo': ['Ativa'],
            'data_inicio': ['Data de Início']
        }

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
                missing_columns.append(possible_names[0])
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")
        
        df = df.rename(columns=column_mapping)
        
        # Formatar datas
        if 'data_inicio' in df.columns:
            df['data_inicio'] = df['data_inicio'].apply(self.format_date)
            
        return df

    def validate_employees_df(self, df):
        """Valida o DataFrame de colaboradores"""
        required_columns = {
            'colaborador': ['Colaborador'],
            'filial': ['Filial'],
            'rede': ['Rede'],
            'ativo': ['Ativo'],
            'data_cadastro': ['Data de Cadastro']
        }

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
                missing_columns.append(possible_names[0])
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")
        
        df = df.rename(columns=column_mapping)
        
        # Formatar datas
        if 'data_cadastro' in df.columns:
            df['data_cadastro'] = df['data_cadastro'].apply(self.format_date)
            
        return df

    def update_networks_and_branches(self, df):
        """Atualiza a base de redes e filiais"""
        conn = sqlite3.connect(self.db_path)
        current_date = datetime.now().strftime('%Y-%m-%d')

        try:
            # Validar e preparar DataFrame
            df = self.validate_networks_df(df)
            
            # Processar redes e filiais
            for _, row in df.iterrows():
                conn.execute('''
                INSERT OR REPLACE INTO networks_branches (
                    nome_rede, nome_filial, ativo, data_inicio, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    row['nome_rede'],
                    row['nome_filial'],
                    row['ativo'],
                    row['data_inicio'],
                    current_date,
                    current_date
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
        current_date = datetime.now().strftime('%Y-%m-%d')

        try:
            # Validar e preparar DataFrame
            df = self.validate_employees_df(df)
            
            # Processar colaboradores
            for _, row in df.iterrows():
                conn.execute('''
                INSERT OR REPLACE INTO employees (
                    colaborador, filial, rede, ativo, data_cadastro, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['colaborador'],
                    row['filial'],
                    row['rede'],
                    row['ativo'],
                    row['data_cadastro'],
                    current_date,
                    current_date
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
                SELECT COUNT(DISTINCT nome_rede) 
                FROM networks_branches 
                WHERE UPPER(ativo) = 'ATIVO'
            ''').fetchone()[0]

            # Total de filiais ativas
            total_branches = conn.execute('''
                SELECT COUNT(DISTINCT nome_filial) 
                FROM networks_branches 
                WHERE UPPER(ativo) = 'ATIVO'
            ''').fetchone()[0]

            # Total de colaboradores ativos
            total_employees = conn.execute('''
                SELECT COUNT(DISTINCT colaborador) 
                FROM employees 
                WHERE UPPER(ativo) = 'ATIVO'
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