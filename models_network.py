import sqlite3
import pandas as pd
from datetime import datetime

class NetworkDatabase:
    def __init__(self):
        self.db_path = 'network_data.db'
        print(f"\n=== Inicializando NetworkDatabase ===")
        print(f"Caminho do banco: {self.db_path}")
        self.init_db()

    def init_db(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        print("\n=== Inicializando banco de dados ===")
        try:
            # Verificar se as tabelas já existem
            existing_tables = c.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND 
                name IN ('networks_branches', 'employees')
            ''').fetchall()
            existing_tables = [t[0] for t in existing_tables]
            
            print(f"Tabelas existentes: {existing_tables}")
            
            # Só criar as tabelas se não existirem
            if 'networks_branches' not in existing_tables:
                print("Criando tabela networks_branches...")
                c.execute('''
                CREATE TABLE networks_branches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_rede TEXT NOT NULL,
                    nome_filial TEXT NOT NULL,
                    ativo TEXT NOT NULL DEFAULT 'ATIVO',
                    data_inicio TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(nome_rede, nome_filial)
                )
                ''')
            else:
                print("Tabela networks_branches já existe")

            if 'employees' not in existing_tables:
                print("Criando tabela employees...")
                c.execute('''
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    colaborador TEXT NOT NULL,
                    filial TEXT NOT NULL,
                    rede TEXT NOT NULL,
                    ativo TEXT NOT NULL DEFAULT 'ATIVO',
                    data_cadastro TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (filial, rede) REFERENCES networks_branches(nome_filial, nome_rede)
                )
                ''')
            else:
                print("Tabela employees já existe")

            conn.commit()
            print("Banco de dados inicializado com sucesso!")
            
            # Verificar estrutura criada
            self.check_database_structure()
            
        except Exception as e:
            print(f"Erro ao inicializar banco: {str(e)}")
            import traceback
            traceback.print_exc()
            conn.rollback()
        finally:
            conn.close()

    def format_date(self, date_str):
        """Formata a data para o formato YYYY-MM-DD"""
        if pd.isna(date_str):
            return datetime.now().strftime('%Y-%m-%d')  # Data atual como fallback
        try:
            return pd.to_datetime(date_str).strftime('%Y-%m-%d')
        except:
            return datetime.now().strftime('%Y-%m-%d')  # Data atual como fallback

    def clean_text(self, text):
        """Limpa e valida texto, retornando um valor não nulo"""
        if pd.isna(text) or not str(text).strip():
            return "NÃO INFORMADO"
        return str(text).strip()

    def validate_networks_df(self, df):
        """Valida o DataFrame de redes e filiais"""
        print("\n=== Validando DataFrame de redes e filiais ===")
        print("Colunas originais:", df.columns.tolist())
        
        # Mapear colunas
        column_mapping = {
            'Nome da Filial': 'nome_filial',
            'Nome da Rede': 'nome_rede',
            'Ativa': 'ativo',
            'Data de Início': 'data_inicio'
        }
        
        # Verificar colunas obrigatórias
        missing_columns = []
        for original, _ in column_mapping.items():
            if original not in df.columns:
                missing_columns.append(original)
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")
        
        # Renomear colunas
        df = df.rename(columns=column_mapping)
        print("Colunas após mapeamento:", df.columns.tolist())
        
        # Limpar e validar dados
        df['nome_rede'] = df['nome_rede'].apply(self.clean_text)
        df['nome_filial'] = df['nome_filial'].apply(self.clean_text)
        df['ativo'] = df['ativo'].apply(lambda x: 'ATIVO' if str(x).upper().strip() in ['SIM', 'S', 'TRUE', '1', 'ATIVO'] else 'INATIVO')
        df['data_inicio'] = df['data_inicio'].apply(self.format_date)
        
        print("\nAmostra após limpeza:")
        print(df.head())
        print(f"Total de registros válidos: {len(df)}")
        
        return df

    def validate_employees_df(self, df):
        """Valida o DataFrame de colaboradores"""
        print("\n=== Validando DataFrame de colaboradores ===")
        print("Colunas originais:", df.columns.tolist())
        
        # Mapear colunas
        column_mapping = {
            'Colaborador': 'colaborador',
            'Filial': 'filial',
            'Rede': 'rede',
            'Ativo': 'ativo',
            'Data de Cadastro': 'data_cadastro'
        }
        
        # Verificar colunas obrigatórias
        missing_columns = []
        for original, _ in column_mapping.items():
            if original not in df.columns:
                missing_columns.append(original)
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")
        
        # Renomear colunas
        df = df.rename(columns=column_mapping)
        print("Colunas após mapeamento:", df.columns.tolist())
        
        # Limpar e validar dados
        df['colaborador'] = df['colaborador'].apply(self.clean_text)
        df['filial'] = df['filial'].apply(self.clean_text)
        df['rede'] = df['rede'].apply(self.clean_text)
        df['ativo'] = df['ativo'].apply(lambda x: 'ATIVO' if str(x).upper().strip() in ['SIM', 'S', 'TRUE', '1', 'ATIVO'] else 'INATIVO')
        df['data_cadastro'] = df['data_cadastro'].apply(self.format_date)
        
        print("\nAmostra após limpeza:")
        print(df.head())
        print(f"Total de registros válidos: {len(df)}")
        
        return df

    def update_networks_and_branches(self, df):
        """Atualiza a base de redes e filiais"""
        conn = sqlite3.connect(self.db_path)
        current_date = datetime.now().strftime('%Y-%m-%d')

        try:
            print("\n=== Atualizando redes e filiais ===")
            
            # Validar e preparar DataFrame
            df = self.validate_networks_df(df)
            
            # Processar redes e filiais
            registros_inseridos = 0
            for _, row in df.iterrows():
                try:
                    # Verificar se todos os campos obrigatórios estão preenchidos
                    if any(pd.isna(row[col]) for col in ['nome_rede', 'nome_filial', 'ativo', 'data_inicio']):
                        print(f"Pulando registro com campos nulos: {row.to_dict()}")
                        continue
                    
                    # Inserir registro
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
                    registros_inseridos += 1
                    
                    if registros_inseridos % 100 == 0:
                        print(f"Processados {registros_inseridos} registros...")
                        
                except Exception as e:
                    print(f"Erro ao inserir registro: {row.to_dict()}")
                    print(f"Erro: {str(e)}")
                    continue

            conn.commit()
            print(f"\nTotal de registros inseridos: {registros_inseridos}")
            
            # Verificar dados após inserção
            total = conn.execute('SELECT COUNT(*) FROM networks_branches').fetchone()[0]
            ativos = conn.execute('''
                SELECT COUNT(*) FROM networks_branches 
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
            ''').fetchone()[0]
            
            print(f"Total de registros na tabela: {total}")
            print(f"Total de registros ativos: {ativos}")
            
            # Mostrar algumas redes inseridas
            redes = conn.execute('''
                SELECT DISTINCT nome_rede, COUNT(*) as total
                FROM networks_branches
                GROUP BY nome_rede
                LIMIT 5
            ''').fetchall()
            
            print("\nAlgumas redes inseridas:")
            for rede in redes:
                print(f"- {rede[0]}: {rede[1]} filiais")
            
            return True, f"Base de redes e filiais atualizada com sucesso! {registros_inseridos} registros inseridos."
        
        except Exception as e:
            conn.rollback()
            print(f"Erro ao atualizar base: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Erro ao atualizar base: {str(e)}"
        
        finally:
            conn.close()

    def update_employees(self, df):
        """Atualiza a base de colaboradores"""
        conn = sqlite3.connect(self.db_path)
        current_date = datetime.now().strftime('%Y-%m-%d')

        try:
            print("\n=== Atualizando colaboradores ===")
            print("DataFrame original:")
            print(df.head())
            print(f"Total de registros: {len(df)}")
            
            # Validar e preparar DataFrame
            df = self.validate_employees_df(df)
            
            print("\nDataFrame após validação:")
            print(df.head())
            print(f"Total de registros após validação: {len(df)}")
            
            # Primeiro, vamos verificar se todas as combinações de filial/rede existem
            existing_branches = pd.read_sql_query('''
                SELECT nome_filial, nome_rede FROM networks_branches
            ''', conn)
            
            print(f"\nFiliais existentes: {len(existing_branches)}")
            
            # Processar colaboradores
            registros_inseridos = 0
            for _, row in df.iterrows():
                try:
                    # Verificar se todos os campos obrigatórios estão preenchidos
                    if any(pd.isna(row[col]) for col in ['colaborador', 'filial', 'rede', 'ativo', 'data_cadastro']):
                        print(f"Pulando registro com campos nulos: {row.to_dict()}")
                        continue
                    
                    # Verificar se a combinação filial/rede existe
                    if not existing_branches[
                        (existing_branches['nome_filial'] == row['filial']) & 
                        (existing_branches['nome_rede'] == row['rede'])
                    ].empty:
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
                        registros_inseridos += 1
                    else:
                        print(f"Filial/rede não encontrada: {row['filial']} / {row['rede']}")
                except Exception as e:
                    print(f"Erro ao inserir registro: {row.to_dict()}")
                    print(f"Erro: {str(e)}")
                    continue

            conn.commit()
            print(f"\nTotal de registros inseridos: {registros_inseridos}")
            
            # Verificar dados após inserção
            total = conn.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
            print(f"Total de registros na tabela: {total}")
            
            return True, f"Base de colaboradores atualizada com sucesso! {registros_inseridos} registros inseridos."
        
        except Exception as e:
            conn.rollback()
            print(f"Erro ao atualizar base: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Erro ao atualizar base: {str(e)}"
        
        finally:
            conn.close()

    def get_network_stats(self):
        """Retorna estatísticas das redes"""
        conn = sqlite3.connect(self.db_path)
        try:
            print("\n=== Consultando estatísticas do banco de dados ===")
            
            # Total de redes ativas
            total_networks = conn.execute('''
                SELECT COUNT(DISTINCT nome_rede) 
                FROM networks_branches 
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
            ''').fetchone()[0]
            
            print(f"Total de redes ativas: {total_networks}")
            
            # Total de filiais ativas
            total_branches = conn.execute('''
                SELECT COUNT(*) 
                FROM networks_branches 
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
            ''').fetchone()[0]
            
            print(f"Total de filiais ativas: {total_branches}")
            
            # Total de colaboradores ativos
            total_employees = conn.execute('''
                SELECT COUNT(*) 
                FROM employees 
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
            ''').fetchone()[0]
            
            print(f"Total de colaboradores ativos: {total_employees}")
            
            # Mostrar algumas redes e suas filiais
            redes = conn.execute('''
                SELECT nome_rede, COUNT(*) as total_filiais
                FROM networks_branches
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
                GROUP BY nome_rede
                LIMIT 5
            ''').fetchall()
            
            print("\nAlgumas redes e suas filiais:")
            for rede in redes:
                print(f"- {rede[0]}: {rede[1]} filiais")

            return {
                'total_networks': total_networks or 0,
                'total_branches': total_branches or 0,
                'total_employees': total_employees or 0
            }

        except Exception as e:
            print(f"Erro ao buscar estatísticas: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'total_networks': 0,
                'total_branches': 0,
                'total_employees': 0
            }
        finally:
            conn.close()

    def debug_data(self):
        """Função auxiliar para debug dos dados"""
        conn = sqlite3.connect(self.db_path)
        try:
            print("\n=== DEBUG: Conteúdo das Tabelas ===")
            
            print("\nRedes e Filiais:")
            networks_data = pd.read_sql_query('''
                SELECT * FROM networks_branches
            ''', conn)
            print(networks_data)
            
            print("\nColaboradores:")
            employees_data = pd.read_sql_query('''
                SELECT * FROM employees
            ''', conn)
            print(employees_data)
            
        except Exception as e:
            print(f"Erro ao debugar dados: {str(e)}")
        finally:
            conn.close()

    def check_database_structure(self):
        """Verifica a estrutura do banco de dados e retorna informações detalhadas"""
        conn = sqlite3.connect(self.db_path)
        try:
            print("\n=== Verificando estrutura do banco de dados ===")
            
            # Verificar tabelas existentes
            tables = conn.execute('''
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND 
                name IN ('networks_branches', 'employees')
            ''').fetchall()
            
            print("\nTabelas encontradas:")
            for table in tables:
                print(f"\nTabela: {table[0]}")
                print("Estrutura SQL:")
                print(table[1])
                
                # Verificar colunas
                columns = conn.execute(f'PRAGMA table_info({table[0]})').fetchall()
                print("\nColunas:")
                for col in columns:
                    print(f"- {col[1]} ({col[2]})")
                
                # Verificar quantidade de registros
                count = conn.execute(f'SELECT COUNT(*) FROM {table[0]}').fetchone()[0]
                print(f"\nTotal de registros: {count}")
                
                # Verificar registros ativos
                if 'ativo' in [col[1] for col in columns]:
                    active_count = conn.execute(f'''
                        SELECT COUNT(*) FROM {table[0]}
                        WHERE UPPER(TRIM(ativo)) = 'ATIVO'
                    ''').fetchone()[0]
                    print(f"Registros ativos: {active_count}")
                
                # Mostrar alguns exemplos de registros
                print("\nExemplos de registros:")
                records = conn.execute(f'SELECT * FROM {table[0]} LIMIT 3').fetchall()
                for record in records:
                    print(record)
            
            return True
            
        except Exception as e:
            print(f"Erro ao verificar estrutura: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close() 