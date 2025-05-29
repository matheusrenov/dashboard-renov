# Glossário de Campos

Este documento descreve em detalhes o significado e uso de cada campo nas bases de dados.

## Base de Redes e Filiais

### Campos da Rede e Filiais
| Campo | Descrição Detalhada | Formato | Regras |
|-------|-------------------|---------|--------|
| Nome da Rede | É o nome da rede parceira, nível mais alto da estrutura organizacional, cada filial desta rede é sua filha na estrutura organizacional. | Texto | Ativa |
| Nome da Filial | Nome da filial pertencente a uma rede. | Texto | Ativa |
| Data de Início | É a data de início da parceria entre a Rede com as suas filiais junto a Renov | Texto | |


## Base de Colaboradores

### Campos do Colaborador
| Campo | Descrição Detalhada | Formato | Regras |
|-------|-------------------|---------|--------|
| Colaborador | Nome do Colaborador de cada Rede e Filial | Texto | Ativo |
| Filial | É a mesma definição de "Nome da filial" | Texto | Ativo |
| Rede |É a mesma definição de "Nome da rede" | Texto | Ativo |
| Ativo | É o status se a filial, rede ou colaborador está ativo ou não para executar avaliação e trade in. | Texto | |
| Data de Cadastro | É a data de cadastro da rede, filial ou colaborador realizado na plataforma da Renov | Texto | |

## Domínios e Valores Permitidos

### Status
- ATIVO/ATIVA: É o status se a filial, rede ou colaborador está ativo ou não para executar avaliação e trade in.




### Cargos


### Estados


## Regras de Negócio
- Uma rede pode ter múltiplas filiais


## Exemplos de Uso

```

## Notas Adicionais

## Como Usar

1. Baixe os arquivos de exemplo:
   - `exemplo_redes_filiais.xlsx`
   - `exemplo_colaboradores.xlsx`

2. Use-os como template, mantendo:
   - Os nomes exatos das colunas
   - Os formatos dos dados
   - As regras de preenchimento

3. Faça o upload na ordem:
   1. Primeiro a base de redes e filiais
   2. Depois a base de colaboradores

## Validações Realizadas

- Unicidade dos códigos
- Existência das colunas obrigatórias
- Formato dos status (ATIVO/INATIVO)
- Relacionamentos entre as bases
- Formato dos dados

## Em Caso de Erros

Se encontrar erros durante o upload, verifique:
1. Se todas as colunas obrigatórias estão presentes
2. Se os nomes das colunas estão exatamente como especificado
3. Se os códigos de relacionamento existem nas bases correspondentes
4. Se os status estão no formato correto