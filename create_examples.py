import pandas as pd
import os
from datetime import datetime, timedelta

# Criar diretório data se não existir
os.makedirs('data', exist_ok=True)

# Criar DataFrame de redes e filiais com exemplos mais completos
redes_filiais = pd.DataFrame({
    'Nome da Rede': ['Rede Sul', 'Rede Sul', 'Rede Norte', 'Rede Norte', 'Rede Centro'],
    'Nome da Filial': ['Filial Porto Alegre', 'Filial Florianópolis', 'Filial Manaus', 'Filial Belém', 'Filial Brasília'],
    'Ativa': ['ATIVO', 'ATIVO', 'ATIVO', 'ATIVO', 'ATIVO'],
    'Data de Início': [
        (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=300)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    ]
})

# Criar DataFrame de colaboradores
colaboradores = pd.DataFrame({
    'Colaborador': ['João Silva', 'Maria Santos', 'Pedro Oliveira', 'Ana Costa', 'Carlos Souza'],
    'Filial': ['Filial Porto Alegre', 'Filial Florianópolis', 'Filial Manaus', 'Filial Belém', 'Filial Brasília'],
    'Rede': ['Rede Sul', 'Rede Sul', 'Rede Norte', 'Rede Norte', 'Rede Centro'],
    'Ativo': ['ATIVO', 'ATIVO', 'ATIVO', 'ATIVO', 'ATIVO'],
    'Data de Cadastro': [
        (datetime.now() - timedelta(days=300)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=250)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=50)).strftime('%Y-%m-%d')
    ]
})

# Salvar arquivos de exemplo
redes_filiais.to_excel('data/exemplo_redes_filiais.xlsx', index=False)
colaboradores.to_excel('data/exemplo_colaboradores.xlsx', index=False)

print("✅ Arquivos de exemplo criados com sucesso!")
print("📁 Verifique a pasta 'data' para encontrar:")
print("   - exemplo_redes_filiais.xlsx")
print("   - exemplo_colaboradores.xlsx") 