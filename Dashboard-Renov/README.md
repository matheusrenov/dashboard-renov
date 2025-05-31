# Dashboard Renov

Dashboard para análise de performance de vouchers e gestão de redes/colaboradores.

## 🚀 Funcionalidades

- Visualização e análise de dados de vouchers
- Gestão de redes e colaboradores
- Monitoramento de performance
- Geração de relatórios e KPIs
- Sistema de autenticação integrado

## 📊 Principais Recursos

- **Visão Geral**: Análise geral de vouchers, valores e distribuição
- **Redes**: Análise detalhada por rede e filial
- **Rankings**: Top vendedores e filiais
- **Projeções**: Análise preditiva de vouchers e valores
- **Engajamento**: Métricas de engajamento de vendedores

## 🛠️ Requisitos

- Python 3.8+
- Dependências listadas em `requirements.txt`

## 📦 Instalação

1. Clone o repositório
2. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Execução

1. Ative o ambiente virtual
2. Execute o servidor:
   ```bash
   python app.py
   ```
3. Acesse http://localhost:8080

## 📁 Estrutura de Arquivos

- `app.py`: Aplicação principal
- `models.py`: Modelos de dados e autenticação
- `models_network.py`: Modelos para redes e colaboradores
- `auth_layout.py`: Layout de autenticação
- `error_layout.py`: Layout de páginas de erro
- `assets/`: Arquivos estáticos (imagens, CSS)
- `data/`: Arquivos de dados e configuração

## 📄 Formatos de Arquivo

### Upload de Dados (Excel)
Colunas obrigatórias:
- Data
- IMEI
- Valor do Voucher
- Valor do Dispositivo
- Status do Voucher
- Vendedor
- Filial
- Rede

### Upload de Redes/Filiais (Excel)
Colunas obrigatórias:
- Nome da Rede
- Nome da Filial
- Data de Início
- Ativo

### Upload de Colaboradores (Excel)
Colunas obrigatórias:
- Colaborador
- Filial
- Rede
- Ativo
- Data de Cadastro

## 👥 Autenticação

O sistema possui autenticação integrada com dois níveis de acesso:
- Administrador
- Usuário padrão

Credenciais padrão:
- Admin: admin/admin123
- Usuário: matheus/admin123

## 🤝 Contribuição

1. Faça o fork do projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. 