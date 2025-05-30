import os
import base64
import io
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from unidecode import unidecode
import warnings
from models import UserDatabase
from models_network import NetworkDatabase
from auth_layout import create_login_layout, create_register_layout, create_admin_approval_layout
from error_layout import create_error_layout
from dash.exceptions import PreventUpdate
from dotenv import load_dotenv
import secrets
from flask_cors import CORS
from flask import Flask, jsonify
import socket
import psutil
from typing import cast, Union, Any, Dict
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from custom_types import PsutilValue, PercentageValue, SystemStatus
from layout import create_upload_section

load_dotenv()  # carrega variáveis do .env se existir

# Inicializa o SQLAlchemy
db = SQLAlchemy()

# ========================
# 🔧 Funções Utilitárias
# ========================

def check_port(port: int) -> bool:
    """Verifica se uma porta está disponível"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return True
        except OSError:
            return False

def get_available_port(start_port: int = 8080) -> int:
    """Encontra uma porta disponível"""
    port = start_port
    while not check_port(port):
        port += 1
        if port > start_port + 100:  # Limite de tentativas
            raise RuntimeError("Não foi possível encontrar uma porta disponível")
    return port

def check_system_health() -> Dict[str, Any]:
    """Verifica a saúde do sistema"""
    try:
        # Verifica uso de CPU
        cpu_percent: float = cast(float, psutil.cpu_percent(interval=1))
        
        # Verifica uso de memória
        memory = psutil.virtual_memory()
        memory_percent: float = cast(float, memory.percent)
        
        # Verifica espaço em disco
        disk = psutil.disk_usage('/')
        disk_percent: float = cast(float, disk.percent)
        
        # Verifica conexão com o banco de dados
        db_status = True
        try:
            user_db = UserDatabase()
            db_status = user_db.test_connection()
        except Exception:
            db_status = False

        # Define o status inicial
        status = 'healthy'
        cpu_status = 'ok'
        memory_status = 'ok'
        disk_status = 'ok'

        # Verifica CPU
        if cpu_percent > 90:
            status = 'unhealthy'
            cpu_status = 'critical'
        elif cpu_percent > 70:
            cpu_status = 'warning'

        # Verifica Memória
        if memory_percent > 90:
            status = 'unhealthy'
            memory_status = 'critical'
        elif memory_percent > 70:
            memory_status = 'warning'

        # Verifica Disco
        if disk_percent > 90:
            status = 'unhealthy'
            disk_status = 'critical'
        elif disk_percent > 70:
            disk_status = 'warning'

        # Se o banco de dados estiver com erro, sistema está unhealthy
        if not db_status:
            status = 'unhealthy'

        return {
            'status': status,
            'cpu': {'value': cpu_percent, 'status': cpu_status},
            'memory': {'value': memory_percent, 'status': memory_status},
            'disk': {'value': disk_percent, 'status': disk_status},
            'database': {'status': 'ok' if db_status else 'error'}
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# ========================
# 🚀 Inicialização do App
# ========================

# Configuração dos assets
assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
if not os.path.exists(assets_path):
    os.makedirs(assets_path)

# Configuração da porta
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'  # Sempre usa 0.0.0.0 para aceitar conexões externas

# Inicialização do Flask
server = Flask(__name__)

# Configurações do Flask para produção/desenvolvimento
server.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(16)),
    DEBUG=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true',
    PORT=PORT,
    HOST=HOST
)

# Configurações de segurança
CORS(server, resources={r"/*": {"origins": "*"}})
server.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)
)

# Configuração de proxy
server.config['PREFERRED_URL_SCHEME'] = 'https'
server.config['PROXY_FIX_X_FOR'] = 1
server.config['PROXY_FIX_X_PROTO'] = 1
server.config['PROXY_FIX_X_HOST'] = 1
server.config['PROXY_FIX_X_PORT'] = 1
server.config['PROXY_FIX_X_PREFIX'] = 1

# Inicialização do Dash com todas as configurações necessárias
app = dash.Dash(
    __name__,
    server=cast(Any, server),
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    update_title='Carregando...',
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ],
    assets_folder=assets_path,
    serve_locally=True,
    routes_pathname_prefix='/'
)

# Layout principal do app
def serve_layout():
    return html.Div([
        dcc.Location(id='url', refresh=False),
        dcc.Store(id='session-store', storage_type='session'),
        dcc.Store(id='error-store', storage_type='session'),
        html.Div(id='page-content', children=create_login_layout()),
        html.Div(id='auth-status'),
        dcc.Store(id='store-data'),
        dcc.Store(id='store-filtered-data')
    ])

# Definição do layout
app.layout = serve_layout

# Vincula o servidor Flask ao Dash
app.server = server
app.title = "Dashboard Renov"

# Endpoint de health check
@server.route('/health')
def health_check():
    try:
        health_status = check_system_health()
        if health_status['status'] == 'error':
            return jsonify(health_status), 500
        elif health_status['status'] == 'unhealthy':
            return jsonify(health_status), 503
        else:
            return jsonify(health_status), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Callback de roteamento principal
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname'),
     Input('error-store', 'data')],
    prevent_initial_call=True
)
def display_page(pathname, error_data):
    ctx = callback_context
    if not ctx.triggered:
        return create_login_layout()

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'error-store' and error_data:
        return create_error_layout(
            error_type=error_data.get('type', 'deploy'),
            error_message=error_data.get('message'),
            error_details=error_data.get('details')
        )

    if not pathname:
        return create_login_layout()
    elif pathname == '/dashboard':
        return create_dashboard_layout()
    elif pathname == '/register':
        return create_register_layout()
    elif pathname == '/error':
        return create_error_layout()
    else:
        return create_login_layout()

def create_dashboard_layout(is_super_admin=False):
    """Cria o layout do dashboard"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H1("📊 Dashboard de Performance Renov",
                       className="text-center mb-4",
                       style={'color': '#2c3e50', 'fontWeight': 'bold'}),
            ], width=10),
            dbc.Col([
                dbc.Button("Sair", id="logout-button", color="danger")
            ], width=2),
            html.Hr(style={'borderColor': '#3498db', 'borderWidth': '2px'})
        ]),

        # Seção de Upload
        create_upload_section(),

        # Welcome Message (mostrado antes do upload)
        html.Div(id='welcome-message', children=[
            html.H4("👋 Bem-vindo ao Dashboard!", className="text-center mt-5"),
            html.P("Faça o upload de um arquivo Excel para começar.", className="text-center text-muted")
        ]),

        # Seção de Filtros (inicialmente oculta)
        html.Div(id='filters-section', style={'display': 'none'}),

        # Seção de KPIs
        html.Div(id='kpi-section'),

        # Seção de Abas (inicialmente oculta)
        html.Div(id='tabs-section', style={'display': 'none'})
    ], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'padding': '20px'})

if __name__ == '__main__':
    try:
        # Configuração inicial
        is_dev = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

        # Mensagens de inicialização
        print("="*50)
        print(f"Iniciando servidor em http://{HOST}:{PORT}")
        print(f"Ambiente: {'development' if is_dev else 'production'}")
        print(f"Debug: {'ativado' if is_dev else 'desativado'}")
        print("="*50)

        # Inicia o servidor
        app.run_server(
            debug=is_dev,
            host=HOST,
            port=PORT,
            dev_tools_hot_reload=False,
            use_reloader=False
        )
    except Exception as e:
        print("="*50)
        print(f"❌ Erro ao iniciar o servidor: {str(e)}")
        print("="*50)
        import traceback
        traceback.print_exc() 