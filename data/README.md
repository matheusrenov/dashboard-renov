# Instruções para Importação de Dados

## Arquivo de Redes e Filiais
O arquivo deve ser um Excel (.xlsx) contendo as seguintes colunas:

- codigo_rede: Código único da rede
- nome_rede: Nome da rede
- status_rede: Status da rede (ATIVA/INATIVA)
- codigo_filial: Código único da filial
- nome_filial: Nome da filial
- status_filial: Status da filial (ATIVA/INATIVA)
- cidade: Cidade da filial
- estado: Estado da filial (UF)
- regiao: Região da filial

## Arquivo de Colaboradores
O arquivo deve ser um Excel (.xlsx) contendo as seguintes colunas:

- codigo_colaborador: Código único do colaborador
- codigo_rede: Código da rede (deve existir na base de redes)
- codigo_filial: Código da filial (deve existir na base de filiais)
- nome: Nome do colaborador
- cargo: Cargo do colaborador
- status: Status do colaborador (ATIVO/INATIVO)

## Observações
- Os arquivos devem estar no formato Excel (.xlsx)
- As colunas podem estar em qualquer ordem
- Os nomes das colunas são case-insensitive e podem conter espaços
- Os códigos (rede, filial, colaborador) devem ser únicos
- Os status devem ser ATIVO/ATIVA ou INATIVO/INATIVA 