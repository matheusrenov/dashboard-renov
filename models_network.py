import sqlite3
import pandas as pd
from datetime import datetime
import os
from unidecode import unidecode

class NetworkDatabase:
    def __init__(self):
        """Inicializa a conexão com o banco de dados"""
        # Usar um caminho absoluto para o banco de dados para garantir persistência
        self.db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'network_data.db')
        
        # Garantir que o diretório data existe
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        
        print(f"\n=== Inicializando NetworkDatabase ===")
        print(f"Caminho do banco: {self.db_file}")
        
        # Criar as tabelas apenas se não existirem
        self.init_db()

    def init_db(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        print("\n=== Verificando estrutura do banco de dados ===")
        try:
            # Verificar se as tabelas já existem
            existing_tables = c.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND 
                name IN ('networks_branches', 'employees')
            ''').fetchall()
            existing_tables = [t[0] for t in existing_tables]
            
            print(f"Tabelas existentes: {existing_tables}")
            
            # Criar tabelas apenas se não existirem
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
                print("Tabela networks_branches criada com sucesso!")
            else:
                print("Tabela networks_branches já existe")
                # Verificar estrutura da tabela existente
                cols = c.execute('PRAGMA table_info(networks_branches)').fetchall()
                print("Colunas existentes:", [col[1] for col in cols])

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
                print("Tabela employees criada com sucesso!")
            else:
                print("Tabela employees já existe")
                # Verificar estrutura da tabela existente
                cols = c.execute('PRAGMA table_info(employees)').fetchall()
                print("Colunas existentes:", [col[1] for col in cols])

            conn.commit()
            
            # Verificar dados existentes
            networks_count = c.execute('SELECT COUNT(*) FROM networks_branches').fetchone()[0]
            employees_count = c.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
            print(f"\nDados existentes:")
            print(f"- Registros em networks_branches: {networks_count}")
            print(f"- Registros em employees: {employees_count}")
            
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
        df['nome_filial'] = df['nome_filial'].apply(self.clean_text)
        
        # Tratar nome_rede: se estiver vazio, usar o nome_filial como nome da rede
        df['nome_rede'] = df.apply(lambda row: 
            self.clean_text(row['nome_filial']) if pd.isna(row['nome_rede']) or str(row['nome_rede']).strip() == '' 
            else self.clean_text(row['nome_rede']), axis=1)
        
        df['ativo'] = df['ativo'].apply(lambda x: 'ATIVO' if str(x).upper().strip() in ['SIM', 'S', 'TRUE', '1', 'ATIVO'] else 'INATIVO')
        df['data_inicio'] = df['data_inicio'].apply(self.format_date)
        
        print("\nAmostra após limpeza:")
        print(df.head())
        print(f"Total de registros válidos: {len(df)}")
        
        # Debug: mostrar contagem de redes únicas
        redes_unicas = df['nome_rede'].unique()
        print(f"\nTotal de redes únicas: {len(redes_unicas)}")
        print("Algumas redes encontradas:")
        for rede in sorted(redes_unicas)[:5]:
            filiais = len(df[df['nome_rede'] == rede])
            print(f"- {rede}: {filiais} filiais")
        
        return df

    def validate_employees_df(self, df):
        """Valida o DataFrame de colaboradores"""
        print("\n=== Validando DataFrame de colaboradores ===")
        print("Colunas originais:", df.columns.tolist())
        
        # Mapear colunas com mais variações possíveis
        column_mapping = {
            'colaborador': ['colaborador', 'nome', 'nome_colaborador', 'funcionario', 'vendedor'],
            'filial': ['filial', 'nome_filial', 'loja', 'nome_da_filial'],
            'rede': ['rede', 'nome_rede', 'network', 'nome_da_rede'],
            'ativo': ['ativo', 'status', 'situacao', 'status_ativo'],
            'data_cadastro': ['data_cadastro', 'data_registro', 'cadastro', 'base_cadastro', 'base_de_cadastro', 'data_base']
        }
        
        # Verificar e mapear colunas
        final_mapping = {}
        missing_columns = []
        
        for target_col, possible_names in column_mapping.items():
            found = False
            for col in df.columns:
                col_normalized = unidecode(str(col)).strip().lower().replace(' ', '_')
                if col_normalized in possible_names:
                    final_mapping[col] = target_col
                    found = True
                    break
            if not found:
                missing_columns.append(target_col)
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")
        
        # Renomear colunas
        df = df.rename(columns=final_mapping)
        print("Colunas após mapeamento:", df.columns.tolist())
        
        # Limpar e validar dados
        df['colaborador'] = df['colaborador'].apply(self.clean_text)
        df['filial'] = df['filial'].apply(self.clean_text)
        df['rede'] = df['rede'].apply(self.clean_text)
        df['ativo'] = df['ativo'].apply(lambda x: 'ATIVO' if str(x).upper().strip() in ['SIM', 'S', 'TRUE', '1', 'ATIVO'] else 'INATIVO')
        
        # Tratamento especial para data_cadastro
        print("\nProcessando datas de cadastro...")
        try:
            df['data_cadastro'] = pd.to_datetime(df['data_cadastro'], errors='coerce')
            print("Exemplo de datas antes da formatação:", df['data_cadastro'].head())
            df['data_cadastro'] = df['data_cadastro'].dt.strftime('%Y-%m-%d')
            print("Exemplo de datas após formatação:", df['data_cadastro'].head())
        except Exception as e:
            print(f"Erro ao processar datas: {str(e)}")
            # Usar data atual como fallback
            df['data_cadastro'] = datetime.now().strftime('%Y-%m-%d')
        
        print("\nAmostra após limpeza:")
        print(df.head())
        print(f"Total de registros válidos: {len(df)}")
        
        return df

    def update_networks_and_branches(self, df):
        """Atualiza a base de redes e filiais"""
        conn = sqlite3.connect(self.db_file)
        current_date = datetime.now().strftime('%Y-%m-%d')

        try:
            print("\n=== Atualizando redes e filiais ===")
            
            # Validar e preparar DataFrame
            df = self.validate_networks_df(df)
            
            # Fazer backup dos dados existentes
            print("Fazendo backup dos dados existentes...")
            backup_count = conn.execute('SELECT COUNT(*) FROM networks_branches').fetchone()[0]
            print(f"Registros no backup: {backup_count}")
            
            # Limpar tabela antes de inserir novos dados
            print("Limpando tabela para nova importação...")
            conn.execute('DELETE FROM networks_branches')
            
            # Processar redes e filiais
            registros_inseridos = 0
            for _, row in df.iterrows():
                try:
                    # Verificar se todos os campos obrigatórios estão preenchidos
                    if pd.isna(row['nome_filial']) or row['nome_filial'].strip() == '':
                        print(f"Pulando registro com nome da filial vazio: {row.to_dict()}")
                        continue
                    
                    # Inserir registro
                    conn.execute('''
                    INSERT INTO networks_branches (
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
        print("\n=== Atualizando base de colaboradores ===")
        try:
            # Verificar se o DataFrame está vazio
            if df.empty:
                return False, "DataFrame vazio"
            
            print("Colunas recebidas:", df.columns.tolist())
            print("Amostra dos dados recebidos:")
            print(df.head())
            
            # Garantir que todas as colunas necessárias existem
            required_columns = ['colaborador', 'filial', 'rede', 'ativo', 'data_cadastro']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                error_msg = f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}"
                print(f"Erro: {error_msg}")
                return False, error_msg
            
            # Limpar e validar dados
            df['colaborador'] = df['colaborador'].apply(self.clean_text)
            df['filial'] = df['filial'].apply(self.clean_text)
            df['rede'] = df['rede'].apply(self.clean_text)
            df['ativo'] = df['ativo'].apply(lambda x: 'ATIVO' if str(x).upper().strip() in ['SIM', 'S', 'TRUE', '1', 'ATIVO'] else 'INATIVO')
            df['data_cadastro'] = df['data_cadastro'].apply(self.format_date)
            
            print("\nDados após limpeza:")
            print(df.head())
            print(f"Total de registros: {len(df)}")
            
            # Verificar se as filiais existem na tabela networks_branches
            conn = sqlite3.connect(self.db_file)
            existing_branches = pd.read_sql_query(
                "SELECT nome_filial, nome_rede FROM networks_branches",
                conn
            )
            
            # Criar um conjunto de tuplas (filial, rede) existentes
            existing_pairs = set(zip(existing_branches['nome_filial'], existing_branches['nome_rede']))
            
            # Verificar pares filial-rede não existentes
            df_pairs = set(zip(df['filial'], df['rede']))
            missing_pairs = df_pairs - existing_pairs
            
            if missing_pairs:
                print("\nAlerta: Algumas filiais não encontradas na base:")
                for filial, rede in list(missing_pairs)[:5]:  # Mostrar apenas os 5 primeiros
                    print(f"- Filial: {filial}, Rede: {rede}")
                
                # Adicionar filiais faltantes automaticamente
                new_branches = pd.DataFrame({
                    'nome_filial': [p[0] for p in missing_pairs],
                    'nome_rede': [p[1] for p in missing_pairs],
                    'ativo': ['ATIVO'] * len(missing_pairs),
                    'data_inicio': [datetime.now().strftime('%Y-%m-%d')] * len(missing_pairs)
                })
                
                print(f"\nAdicionando {len(missing_pairs)} novas filiais à base...")
                self.update_networks_and_branches(new_branches)
            
            # Timestamp para created_at e updated_at
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Inserir ou atualizar colaboradores
            cursor = conn.cursor()
            
            # Primeiro, desativar todos os colaboradores existentes
            cursor.execute("UPDATE employees SET ativo = 'INATIVO', updated_at = ?", (current_time,))
            
            # Depois, inserir ou atualizar os novos registros
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO employees (
                        colaborador, filial, rede, ativo, data_cadastro, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(colaborador, filial, rede) DO UPDATE SET
                        ativo = excluded.ativo,
                        updated_at = excluded.updated_at
                """, (
                    row['colaborador'],
                    row['filial'],
                    row['rede'],
                    row['ativo'],
                    row['data_cadastro'],
                    current_time,
                    current_time
                ))
            
            conn.commit()
            
            # Verificar resultados
            total_employees = cursor.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
            active_employees = cursor.execute("SELECT COUNT(*) FROM employees WHERE ativo = 'ATIVO'").fetchone()[0]
            
            print("\nResultados da atualização:")
            print(f"Total de colaboradores na base: {total_employees}")
            print(f"Colaboradores ativos: {active_employees}")
            
            conn.close()
            return True, "Base de colaboradores atualizada com sucesso!"
            
        except Exception as e:
            print(f"Erro ao atualizar colaboradores: {str(e)}")
            import traceback
            traceback.print_exc()
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False, str(e)

    def get_network_stats(self):
        """Retorna estatísticas das redes"""
        conn = sqlite3.connect(self.db_file)
        try:
            print("\n=== Consultando estatísticas do banco de dados ===")
            
            # Total de redes ativas (contagem distinta de nome_rede)
            total_networks = conn.execute('''
                SELECT COUNT(DISTINCT nome_rede) 
                FROM networks_branches 
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
            ''').fetchone()[0]
            
            print(f"Total de redes ativas: {total_networks}")
            
            # Debug: mostrar redes encontradas
            redes = conn.execute('''
                SELECT DISTINCT nome_rede, COUNT(*) as total_filiais
                FROM networks_branches
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
                GROUP BY nome_rede
                ORDER BY nome_rede
            ''').fetchall()
            
            print("\nRedes ativas encontradas:")
            for rede in redes:
                print(f"- {rede[0]}: {rede[1]} filiais")
            
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
        conn = sqlite3.connect(self.db_file)
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
        conn = sqlite3.connect(self.db_file)
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

    def get_executive_summary(self):
        """Retorna o resumo executivo com totais por rede"""
        conn = sqlite3.connect(self.db_file)
        try:
            # Consulta para obter totais por rede
            query = '''
            WITH rede_stats AS (
                -- Contagem de filiais por rede
                SELECT 
                    nb.nome_rede,
                    COUNT(DISTINCT nb.nome_filial) as total_filiais,
                    COUNT(DISTINCT e.colaborador) as total_colaboradores
                FROM networks_branches nb
                LEFT JOIN employees e ON e.rede = nb.nome_rede 
                    AND e.filial = nb.nome_filial
                    AND UPPER(TRIM(e.ativo)) = 'ATIVO'
                WHERE UPPER(TRIM(nb.ativo)) = 'ATIVO'
                GROUP BY nb.nome_rede
            )
            SELECT 
                nome_rede as "Nome da Rede",
                total_filiais as "Total de Filiais",
                total_colaboradores as "Total de Colaboradores"
            FROM rede_stats
            ORDER BY total_filiais DESC, nome_rede ASC
            '''
            
            df = pd.read_sql_query(query, conn)
            return df
            
        except Exception as e:
            print(f"Erro ao gerar resumo executivo: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
        finally:
            conn.close()

    def get_evolution_data(self):
        """Retorna dados para os gráficos evolutivos mensais"""
        conn = sqlite3.connect(self.db_file)
        try:
            # Consulta para evolução de redes
            networks_query = '''
            WITH RECURSIVE dates(date) AS (
                SELECT MIN(date(data_inicio, 'start of month'))
                FROM networks_branches
                UNION ALL
                SELECT date(date, '+1 month')
                FROM dates
                WHERE date < (SELECT MAX(date(data_inicio, 'start of month')) FROM networks_branches)
            ),
            monthly_networks AS (
                SELECT 
                    date(data_inicio, 'start of month') as month,
                    COUNT(DISTINCT nome_rede) as total_redes
                FROM networks_branches
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
                GROUP BY date(data_inicio, 'start of month')
            )
            SELECT 
                strftime('%Y-%m', dates.date) as mes,
                SUM(monthly_networks.total_redes) OVER (ORDER BY dates.date) as total_redes
            FROM dates
            LEFT JOIN monthly_networks ON strftime('%Y-%m', dates.date) = strftime('%Y-%m', monthly_networks.month)
            ORDER BY dates.date
            '''
            
            # Consulta para evolução de filiais
            branches_query = '''
            WITH RECURSIVE dates(date) AS (
                SELECT MIN(date(data_inicio, 'start of month'))
                FROM networks_branches
                UNION ALL
                SELECT date(date, '+1 month')
                FROM dates
                WHERE date < (SELECT MAX(date(data_inicio, 'start of month')) FROM networks_branches)
            ),
            monthly_branches AS (
                SELECT 
                    date(data_inicio, 'start of month') as month,
                    COUNT(*) as total_filiais
                FROM networks_branches
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
                GROUP BY date(data_inicio, 'start of month')
            )
            SELECT 
                strftime('%Y-%m', dates.date) as mes,
                SUM(monthly_branches.total_filiais) OVER (ORDER BY dates.date) as total_filiais
            FROM dates
            LEFT JOIN monthly_branches ON strftime('%Y-%m', dates.date) = strftime('%Y-%m', monthly_branches.month)
            ORDER BY dates.date
            '''
            
            # Consulta para evolução de colaboradores
            employees_query = '''
            WITH RECURSIVE dates(date) AS (
                SELECT MIN(date(data_cadastro, 'start of month'))
                FROM employees
                UNION ALL
                SELECT date(date, '+1 month')
                FROM dates
                WHERE date < (SELECT MAX(date(data_cadastro, 'start of month')) FROM employees)
            ),
            monthly_employees AS (
                SELECT 
                    date(data_cadastro, 'start of month') as month,
                    COUNT(*) as total_colaboradores
                FROM employees
                WHERE UPPER(TRIM(ativo)) = 'ATIVO'
                GROUP BY date(data_cadastro, 'start of month')
            )
            SELECT 
                strftime('%Y-%m', dates.date) as mes,
                SUM(monthly_employees.total_colaboradores) OVER (ORDER BY dates.date) as total_colaboradores
            FROM dates
            LEFT JOIN monthly_employees ON strftime('%Y-%m', dates.date) = strftime('%Y-%m', monthly_employees.month)
            ORDER BY dates.date
            '''
            
            networks_df = pd.read_sql_query(networks_query, conn)
            branches_df = pd.read_sql_query(branches_query, conn)
            employees_df = pd.read_sql_query(employees_query, conn)
            
            # Combinar todos os dados em um único DataFrame
            df = networks_df.merge(branches_df, on='mes', how='outer')
            df = df.merge(employees_df, on='mes', how='outer')
            
            # Preencher valores nulos
            df = df.fillna(0)
            
            # Converter mês para formato mais amigável
            df['mes'] = pd.to_datetime(df['mes']).dt.strftime('%b/%Y')
            
            return df
            
        except Exception as e:
            print(f"Erro ao gerar dados evolutivos: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
        finally:
            conn.close()

    def get_all_employees(self) -> pd.DataFrame:
        """
        Retorna todos os colaboradores cadastrados no banco de dados
        
        Returns:
            DataFrame com as colunas: nome, filial, rede, ativo, data_cadastro
        """
        try:
            conn = sqlite3.connect(self.db_file)
            query = """
            SELECT 
                e.colaborador as nome,
                e.filial,
                e.rede,
                e.ativo,
                e.data_cadastro
            FROM employees e
            JOIN networks_branches nb ON e.filial = nb.nome_filial AND e.rede = nb.nome_rede
            WHERE UPPER(TRIM(e.ativo)) = 'ATIVO'
            ORDER BY e.rede, e.filial, e.colaborador
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            print(f"Erro ao obter colaboradores: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame() 