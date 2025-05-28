import pandas as pd
import os

# Criar diretório data se não existir
os.makedirs('data', exist_ok=True)

# Criar DataFrame de redes e filiais
redes_filiais = pd.DataFrame({
    'codigo_rede': ['RED001', 'RED002'],
    'nome_rede': ['Rede Exemplo', 'Rede Teste'],
    'status_rede': ['ATIVA', 'ATIVA'],
    'codigo_filial': ['FIL001', 'FIL002'],
    'nome_filial': ['Filial Centro', 'Filial Norte'],
    'status_filial': ['ATIVA', 'ATIVA'],
    'cidade': ['São Paulo', 'Rio de Janeiro'],
    'estado': ['SP', 'RJ'],
    'regiao': ['Sudeste', 'Sudeste']
})

# Criar DataFrame de colaboradores
colaboradores = pd.DataFrame({
    'codigo_colaborador': ['COL001', 'COL002', 'COL003'],
    'codigo_rede': ['RED001', 'RED001', 'RED002'],
    'codigo_filial': ['FIL001', 'FIL001', 'FIL002'],
    'nome': ['João Silva', 'Maria Santos', 'Pedro Souza'],
    'cargo': ['Vendedor', 'Gerente', 'Vendedor'],
    'status': ['ATIVO', 'ATIVO', 'ATIVO']
})

# Salvar como Excel
redes_filiais.to_excel('data/exemplo_redes_filiais.xlsx', index=False)
colaboradores.to_excel('data/exemplo_colaboradores.xlsx', index=False)

print("Arquivos de exemplo criados com sucesso!") 