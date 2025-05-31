# -*- coding: utf-8 -*-
"""
Dashboard Renov - Aplicação principal

Este módulo contém a aplicação principal do Dashboard Renov, responsável por:
- Visualização e análise de dados de vouchers
- Gestão de redes e colaboradores
- Monitoramento de performance
- Geração de relatórios e KPIs
"""

# Bibliotecas padrão
import os
import io
import base64
import secrets
import traceback
import socket
from datetime import datetime, timedelta
from typing import TypeVar, TypedDict, Literal, Optional, cast

# Bibliotecas de dados e análise
import pandas as pd
import numpy as np
from unidecode import unidecode

# Monitoramento do sistema
import psutil

# Flask e extensões
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Dash e componentes
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, dash_table, callback_context, no_update
from dash.exceptions import PreventUpdate

# Plotly para gráficos
import plotly.graph_objects as go
import plotly.express as px

# Exportação de dados
import xlsxwriter

# Módulos locais
from models import UserDatabase
from models_network import NetworkDatabase
from auth_layout import create_login_layout, create_register_layout, create_admin_approval_layout
from error_layout import create_error_layout
from custom_types import PsutilValue, PercentageValue, SystemStatus, ResourceStatus, DatabaseStatus

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()  # carrega variáveis do .env se existir

# Tipos personalizados
PsutilValue = TypeVar('PsutilValue', float, int)
PercentageValue = float

class ResourceStatus(TypedDict):
    value: float
    status: Literal['ok', 'warning', 'critical']

class DatabaseStatus(TypedDict):
    status: Literal['ok', 'error']

class SystemStatus(TypedDict):
    status: Literal['healthy', 'unhealthy', 'error']
    cpu: ResourceStatus
    memory: ResourceStatus
    disk: ResourceStatus
    database: DatabaseStatus
    message: Optional[str]

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

def check_system_health() -> SystemStatus:
    """Verifica a saúde do sistema"""
    try:
        # Verifica uso de CPU
        cpu_percent = cast(float, psutil.cpu_percent(interval=1))
        cpu_status: ResourceStatus = {
            'value': cpu_percent,
            'status': 'critical' if cpu_percent > 90 else 'warning' if cpu_percent > 70 else 'ok'
        }
        
        # Verifica uso de memória
        memory = psutil.virtual_memory()
        memory_percent = cast(float, memory.percent)
        memory_status: ResourceStatus = {
            'value': memory_percent,
            'status': 'critical' if memory_percent > 90 else 'warning' if memory_percent > 70 else 'ok'
        }
        
        # Verifica espaço em disco
        disk = psutil.disk_usage('/')
        disk_percent = cast(float, disk.percent)
        disk_status: ResourceStatus = {
            'value': disk_percent,
            'status': 'critical' if disk_percent > 90 else 'warning' if disk_percent > 70 else 'ok'
        }
        
        # Verifica conexão com o banco de dados
        db_status: DatabaseStatus = {'status': 'ok'}
        try:
            user_db = UserDatabase()
            if not user_db.test_connection():
                db_status = {'status': 'error'}
        except Exception:
            db_status = {'status': 'error'}
        
        # Define o status inicial
        system_status: SystemStatus = {
            'status': 'healthy',
            'cpu': cpu_status,
            'memory': memory_status,
            'disk': disk_status,
            'database': db_status,
            'message': None
        }
        
        # Verifica condições críticas
        if (cpu_status['status'] == 'critical' or 
            memory_status['status'] == 'critical' or 
            disk_status['status'] == 'critical' or 
            db_status['status'] == 'error'):
            system_status['status'] = 'unhealthy'
        
        return system_status
    
    except Exception as e:
        error_status: SystemStatus = {
            'status': 'error',
            'cpu': {'value': 0.0, 'status': 'critical'},
            'memory': {'value': 0.0, 'status': 'critical'},
            'disk': {'value': 0.0, 'status': 'critical'},
            'database': {'status': 'error'},
            'message': str(e)
        }
        return error_status

# ========================
# 🚀 Inicialização do App
# ========================

# Configuração dos assets
assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
if not os.path.exists(assets_path):
    os.makedirs(assets_path)

# Configuração da porta
# Em produção, usa a porta fornecida pelo ambiente ou 8080 como fallback
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'  # Sempre usa 0.0.0.0 para aceitar conexões externas

# Inicialização do Flask
server = Flask(__name__)

# Inicialização do Dash com todas as configurações necessárias
app = dash.Dash(
    __name__,
    server=server,
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

# Configuração do CORS
CORS(server)

# Configuração do banco de dados
server.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/network_data.db'
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(server)

# Rota de health check
@server.route('/health')
def health_check():
    """Endpoint para verificar a saúde do sistema"""
    status = check_system_health()
    return jsonify(status)

def serve_layout():
    """Função que serve o layout dinâmico do app"""
    return html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
    ])

app.layout = serve_layout

def create_dashboard_layout(is_super_admin=False):
    """Cria o layout principal do dashboard"""
    return html.Div([
        # Navbar
        dbc.Navbar(
            dbc.Container([
                html.A(
                    dbc.Row([
                        dbc.Col(html.Img(src="/assets/logo.png", height="30px")),
                        dbc.Col(dbc.NavbarBrand("Dashboard Renov", className="ms-2")),
                    ], align="center", className="g-0"),
                    href="/",
                    style={"textDecoration": "none"},
                ),
                dbc.NavbarToggler(id="navbar-toggler"),
                dbc.Collapse(
                    dbc.Nav([
                        dbc.NavItem(dbc.Button("Logout", id="logout-button", color="light", className="ms-2")),
                    ], className="ms-auto", navbar=True),
                    id="navbar-collapse",
                    navbar=True,
                ),
            ]),
            color="primary",
            dark=True,
            className="mb-4",
        ),
        
        # Conteúdo principal
        dbc.Container([
            # Área de upload
            dbc.Card([
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Arraste e solte ou ',
                            html.A('selecione um arquivo Excel')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px 0'
                        },
                        multiple=False
                    ),
                    html.Div(id='upload-status')
                ])
            ], className="mb-4"),
            
            # Área de filtros
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Mês"),
                            dcc.Dropdown(id='filter-month', multi=True)
                        ], md=3),
                        dbc.Col([
                            html.Label("Rede"),
                            dcc.Dropdown(id='filter-network', multi=True)
                        ], md=3),
                        dbc.Col([
                            html.Label("Status"),
                            dcc.Dropdown(id='filter-status', multi=True)
                        ], md=3),
                        dbc.Col([
                            html.Label("Data Inicial"),
                            dcc.DatePickerSingle(id='filter-start-date')
                        ], md=1),
                        dbc.Col([
                            html.Label("Data Final"),
                            dcc.DatePickerSingle(id='filter-end-date')
                        ], md=1),
                        dbc.Col([
                            html.Br(),
                            dbc.Button("Limpar Filtros", id="clear-filters", color="secondary", size="sm")
                        ], md=1)
                    ])
                ])
            ], className="mb-4", id="filters-section", style={'display': 'none'}),
            
            # KPIs
            html.Div(id='kpi-section', style={'display': 'none'}),
            
            # Abas principais
            dbc.Tabs([
                dbc.Tab(label="Visão Geral", tab_id="tab-overview"),
                dbc.Tab(label="TIM", tab_id="tab-tim"),
                dbc.Tab(label="Rankings", tab_id="tab-rankings"),
                dbc.Tab(label="Projeções", tab_id="tab-projections"),
                dbc.Tab(label="Base de Redes", tab_id="tab-network-base"),
                dbc.Tab(label="Engajamento", tab_id="tab-engagement")
            ], id="main-tabs", active_tab="tab-overview"),
            
            # Área de conteúdo das abas
            html.Div(id="tab-content-area", className="mt-4"),
            
            # Armazenamento de dados
            dcc.Store(id='store-data'),
            dcc.Store(id='store-filtered-data'),
            
            # Download de dados
            dcc.Download(id="download-excel")
        ], fluid=True)
    ])

def generate_kpi_cards(df):
    """Gera cards com KPIs principais"""
    try:
        total_vouchers = len(df)
        used_vouchers = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        total_used = len(used_vouchers)
        
        total_value = used_vouchers['valor_dispositivo'].sum()
        avg_ticket = total_value / total_used if total_used > 0 else 0
        conversion_rate = (total_used / total_vouchers * 100) if total_vouchers > 0 else 0
        
        total_stores = df['nome_filial'].nunique()
        active_stores = used_vouchers['nome_filial'].nunique() if not used_vouchers.empty else 0
        
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Vouchers Totais", className="card-title text-muted mb-2"),
                        html.H3(f"{total_vouchers:,}", className="text-info fw-bold mb-1")
                    ])
                ], className="h-100 shadow-sm border-0")
            ], md=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Vouchers Utilizados", className="card-title text-muted mb-2"),
                        html.H3(f"{total_used:,}", className="text-success fw-bold mb-1"),
                        html.Small(f"{conversion_rate:.1f}% conversão", className="text-muted")
                    ])
                ], className="h-100 shadow-sm border-0")
            ], md=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Valor Total", className="card-title text-muted mb-2"),
                        html.H3(f"R$ {total_value:,.2f}", className="text-warning fw-bold mb-1")
                    ])
                ], className="h-100 shadow-sm border-0")
            ], md=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Ticket Médio", className="card-title text-muted mb-2"),
                        html.H3(f"R$ {avg_ticket:,.2f}", className="text-primary fw-bold mb-1")
                    ])
                ], className="h-100 shadow-sm border-0")
            ], md=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Lojas Totais", className="card-title text-muted mb-2"),
                        html.H3(f"{total_stores}", className="text-danger fw-bold mb-1")
                    ])
                ], className="h-100 shadow-sm border-0")
            ], md=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Lojas Ativas", className="card-title text-muted mb-2"),
                        html.H3(f"{active_stores}", className="text-dark fw-bold mb-1"),
                        html.Small(f"{(active_stores/total_stores*100):.1f}% do total", className="text-muted")
                    ])
                ], className="h-100 shadow-sm border-0")
            ], md=2)
        ], className="g-2 mb-4")
    except Exception as e:
        print(f"Erro ao gerar KPIs: {str(e)}")
        traceback.print_exc()
        return html.Div()

if __name__ == '__main__':
    app.run_server(host=HOST, port=PORT, debug=True)