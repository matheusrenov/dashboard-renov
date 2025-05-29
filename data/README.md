# Estrutura do Banco de Dados

Este diretório contém o banco de dados SQLite (`network_data.db`) que armazena as informações de redes, filiais e colaboradores.

## Persistência dos Dados

O banco de dados é persistente e só é atualizado quando:
1. Um novo arquivo de redes/filiais é enviado através do botão "Atualizar Base de Redes e Filiais"
2. Um novo arquivo de colaboradores é enviado através do botão "Atualizar Base de Colaboradores"

Os dados permanecem intactos entre:
- Reinicializações do servidor
- Novos deploys
- Acessos de diferentes usuários

## Estrutura das Tabelas

### networks_branches
Armazena informações sobre redes e filiais.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INTEGER | ID único do registro |
| nome_rede | TEXT | Nome da rede (ou nome da filial quando é rede independente) |
| nome_filial | TEXT | Nome da filial |
| ativo | TEXT | Status (ATIVO/INATIVO) |
| data_inicio | TEXT | Data de início no formato YYYY-MM-DD |
| created_at | TEXT | Data de criação do registro |
| updated_at | TEXT | Data da última atualização |

### employees
Armazena informações sobre colaboradores.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INTEGER | ID único do registro |
| colaborador | TEXT | Nome do colaborador |
| filial | TEXT | Nome da filial onde trabalha |
| rede | TEXT | Nome da rede à qual pertence |
| ativo | TEXT | Status (ATIVO/INATIVO) |
| data_cadastro | TEXT | Data de cadastro no formato YYYY-MM-DD |
| created_at | TEXT | Data de criação do registro |
| updated_at | TEXT | Data da última atualização |

## Estrutura dos Arquivos de Upload

### Arquivo de Redes e Filiais
O arquivo Excel deve conter as seguintes colunas:
- Nome da Filial (obrigatório)
- Nome da Rede (opcional - se vazio, usa o nome da filial como rede)
- Ativa (SIM/NÃO)
- Data de Início (formato de data)

### Arquivo de Colaboradores
O arquivo Excel deve conter as seguintes colunas:
- Colaborador (obrigatório)
- Filial (obrigatório)
- Rede (obrigatório)
- Ativo (SIM/NÃO)
- Data de Cadastro (formato de data)

## Observações Importantes

1. O banco de dados é criado automaticamente na primeira execução
2. As tabelas são criadas apenas se não existirem
3. Ao fazer upload de novos dados, os dados antigos da respectiva tabela são substituídos
4. Mantenha backup regular do arquivo `network_data.db` para evitar perda de dados 