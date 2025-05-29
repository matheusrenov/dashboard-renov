import pandas as pd
import os
from datetime import datetime, timedelta

# Criar diretório data se não existir
os.makedirs('data', exist_ok=True)

# Função auxiliar para formatar data
def format_date(days_ago):
    return (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')

# Criar DataFrame de redes e filiais com exemplos mais completos
redes_filiais = pd.DataFrame({
    'Nome da Rede': ['Rede Sul', 'Rede Sul', 'Rede Norte', 'Rede Norte', 'Rede Centro'],
    'Nome da Filial': ['Filial Porto Alegre', 'Filial Florianópolis', 'Filial Manaus', 'Filial Belém', 'Filial Brasília'],
    'Ativa': ['ATIVO', 'ATIVO', 'ATIVO', 'ATIVO', 'ATIVO'],
    'Data de Início': [
        format_date(365),
        format_date(300),
        format_date(180),
        format_date(150),
        format_date(90)
    ]
})

# Criar DataFrame de colaboradores
colaboradores = pd.DataFrame({
    'Colaborador': ['João Silva', 'Maria Santos', 'Pedro Oliveira', 'Ana Costa', 'Carlos Souza'],
    'Filial': ['Filial Porto Alegre', 'Filial Florianópolis', 'Filial Manaus', 'Filial Belém', 'Filial Brasília'],
    'Rede': ['Rede Sul', 'Rede Sul', 'Rede Norte', 'Rede Norte', 'Rede Centro'],
    'Ativo': ['ATIVO', 'ATIVO', 'ATIVO', 'ATIVO', 'ATIVO'],
    'Data de Cadastro': [
        format_date(300),
        format_date(250),
        format_date(150),
        format_date(100),
        format_date(50)
    ]
})

# Salvar arquivos de exemplo
redes_filiais.to_excel('data/exemplo_redes_filiais.xlsx', index=False)
colaboradores.to_excel('data/exemplo_colaboradores.xlsx', index=False)

print("✅ Arquivos de exemplo criados com sucesso!")
print("📁 Verifique a pasta 'data' para encontrar:")
print("   - exemplo_redes_filiais.xlsx")
print("   - exemplo_colaboradores.xlsx") 