# Dashboard Renov 📊

Um dashboard moderno e responsivo para análise de dados de vouchers e gestão de redes.

## 🚀 Funcionalidades

- **Análise de Dados**
  - Upload e processamento de arquivos Excel
  - Visualização de KPIs em tempo real
  - Gráficos e tabelas interativas
  - Filtros dinâmicos por período, rede e status

- **Gestão de Redes**
  - Cadastro e monitoramento de redes e filiais
  - Gestão de colaboradores
  - Análise de performance por rede/filial
  - Indicadores de engajamento

- **Segurança**
  - Sistema de autenticação robusto
  - Controle de acesso baseado em papéis
  - Proteção contra ataques comuns
  - Sessões seguras e criptografadas

## 🛠️ Tecnologias

- Python 3.8+
- Dash/Plotly
- Flask
- SQLAlchemy
- PostgreSQL
- Bootstrap
- Docker

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- PostgreSQL
- Docker (opcional)

## 🔧 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/renovsmart/dashboard-renov.git
cd dashboard-renov
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Para desenvolvimento
```

4. Configure o ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. Inicialize o banco de dados:
```bash
flask db upgrade
```

## 🚀 Execução

### Desenvolvimento
```bash
python app.py
```

### Produção
```bash
gunicorn wsgi:server
```

## 🧪 Testes

```bash
# Executar todos os testes
pytest

# Com cobertura de código
pytest --cov=app --cov-report=html

# Testes específicos
pytest tests/test_specific.py
```

## 🔍 Qualidade de Código

### Pre-commit hooks

Instale e configure os hooks do pre-commit:
```bash
pre-commit install
```

Execute manualmente:
```bash
pre-commit run --all-files
```

### Linting e Formatação

```bash
# Formatação com Black
black .

# Ordenação de imports
isort .

# Verificação de tipos com MyPy
mypy .

# Análise de código com Flake8
flake8 .

# Análise de segurança com Bandit
bandit -r .

# Verificação de dependências com Safety
safety check
```

## 📚 Documentação

A documentação está disponível em `docs/` e pode ser construída usando Sphinx:

```bash
cd docs
make html
```

Acesse a documentação em `docs/_build/html/index.html`.

## 🔄 CI/CD

O projeto utiliza GitHub Actions para:
- Testes automatizados
- Análise de qualidade de código
- Verificação de segurança
- Deploy automático
- Atualização de dependências

## 🤝 Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para mais detalhes.

## 📝 Licença

Este projeto está sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📧 Contato

Renov Smart - contato@renovsmart.com.br

Link do projeto: [https://github.com/renovsmart/dashboard-renov](https://github.com/renovsmart/dashboard-renov)

## 📁 Estrutura do Projeto

```
dashboard-renov/
├── app.py              # Aplicação principal
├── wsgi.py            # Entrada para produção
├── requirements.txt   # Dependências
├── utils.py          # Funções utilitárias
├── custom_types.py   # Tipos personalizados
├── models/           # Modelos de dados
├── layouts/          # Layouts da interface
├── callbacks/        # Callbacks do Dash
├── assets/          # Arquivos estáticos
└── data/            # Dados e banco SQLite
```

## 📊 Formatos de Dados

### Arquivo de Vouchers
- IMEI/ID do Dispositivo
- Data de Criação
- Valor do Voucher
- Valor do Dispositivo
- Situação do Voucher
- Nome do Vendedor
- Nome da Filial
- Nome da Rede

### Arquivo de Redes
- Nome da Rede
- Nome da Filial
- Data de Início

### Arquivo de Colaboradores
- Nome
- Filial
- Rede
- Status Ativo
- Data de Cadastro

## 🔐 Variáveis de Ambiente

```env
FLASK_DEBUG=False
SECRET_KEY=your_secret_key_here
PORT=8080
DATABASE_URL=sqlite:///data/dashboard.db
```

## 🛡️ Segurança

- Todas as senhas são hasheadas com bcrypt
- Sessões são protegidas e expiram após 30 minutos
- CORS configurado para maior segurança
- Proteção contra CSRF implementada
- Validação de entrada em todos os formulários

## 📈 Monitoramento

O sistema inclui monitoramento automático de:
- Uso de CPU
- Uso de Memória
- Espaço em Disco
- Status do Banco de Dados
- Performance da Aplicação

## 📄 Comandos Úteis

- `

## Configurações

O sistema utiliza variáveis de ambiente para configuração. Copie o arquivo `.env.example` para `.env` e configure conforme necessário:

### Servidor
- `PORT`: Porta do servidor (padrão: 8050)
- `HOST`: Host do servidor (padrão: 0.0.0.0)
- `FLASK_DEBUG`: Modo debug (padrão: False)

### Banco de Dados
- `DB_HOST`: Host do banco de dados (padrão: localhost)
- `DB_PORT`: Porta do banco de dados (padrão: 5432)
- `DB_NAME`: Nome do banco de dados (padrão: dashboard)
- `DB_USER`: Usuário do banco de dados (padrão: postgres)
- `DB_PASSWORD`: Senha do banco de dados

### Cache
- `CACHE_TYPE`: Tipo de cache (simple, redis)
- `CACHE_REDIS_URL`: URL do Redis (se usado)

### Segurança
- `SECRET_KEY`: Chave secreta para sessões
- `CSRF_SESSION_KEY`: Chave para proteção CSRF

### Email
- `SMTP_HOST`: Host do servidor SMTP
- `SMTP_PORT`: Porta do servidor SMTP
- `SMTP_USER`: Usuário SMTP
- `SMTP_PASSWORD`: Senha SMTP
- `SMTP_USE_TLS`: Usar TLS (True/False)
- `EMAIL_FROM`: Email remetente

### Logging
- `LOG_LEVEL`: Nível de log (INFO, DEBUG, etc)
- `LOG_FILE`: Arquivo de log

### Monitoramento
- `HEALTHCHECK_INTERVAL`: Intervalo do healthcheck (segundos)
- `METRICS_INTERVAL`: Intervalo de coleta de métricas (segundos)
- `BACKUP_RETENTION_DAYS`: Dias de retenção dos backups

### Limiares do Sistema
- `CPU_WARNING`: Limite de alerta para CPU (%)
- `CPU_CRITICAL`: Limite crítico para CPU (%)
- `MEMORY_WARNING`: Limite de alerta para memória (%)
- `MEMORY_CRITICAL`: Limite crítico para memória (%)
- `DISK_WARNING`: Limite de alerta para disco (%)
- `DISK_CRITICAL`: Limite crítico para disco (%)

## Instalação

1. Clone o repositório
```bash
git clone https://github.com/renovsmart/dashboard-renov.git
cd dashboard-renov
```

2. Crie e ative o ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. Instale as dependências
```bash
pip install -r requirements.txt
```

4. Configure o ambiente
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. Inicialize o banco de dados
```bash
flask db upgrade
```

6. Execute o servidor
```bash
python app.py
```

## Desenvolvimento

Para ambiente de desenvolvimento:

1. Instale as dependências de desenvolvimento
```bash
pip install -r requirements-dev.txt
```

2. Configure o pre-commit
```bash
pre-commit install
```

3. Execute os testes
```bash
pytest
```

## Deploy

Para deploy em produção:

1. Configure o servidor web (Nginx)
```bash
sudo cp nginx/conf.d/default.conf /etc/nginx/conf.d/
sudo systemctl restart nginx
```

2. Configure o serviço systemd
```bash
sudo cp dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dashboard
sudo systemctl start dashboard
```

3. Configure os backups
```bash
sudo cp backup.sh /etc/cron.daily/dashboard-backup
sudo chmod +x /etc/cron.daily/dashboard-backup
```

## Monitoramento

O sistema inclui ferramentas de monitoramento:

- Healthcheck: `/health`
- Métricas: `/metrics`
- Logs: `logs/dashboard.log`
- Alertas: `logs/dashboard-alerts.log`

## Licença

Copyright © 2024 Renov Smart. Todos os direitos reservados.
