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
from typing import Dict, Any, Union, cast, TypeVar

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

# Tipos personalizados
PsutilValue = TypeVar('PsutilValue', float, int)
PercentageValue = float
SystemStatus = Dict[str, Union[
    str,
    Dict[str, Union[PsutilValue, str]],
    Dict[str, str],
    str
]]

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()  # carrega variáveis do .env se existir

# Configuração dos assets
assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
if not os.path.exists(assets_path):
    os.makedirs(assets_path)

# Configuração da porta
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'

# Inicialização do Flask
server = Flask(__name__)

# Configurações do Flask
server.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(16)),
    FLASK_ENV='production',
    DEBUG=False,
    PORT=PORT,
    HOST=HOST,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    PREFERRED_URL_SCHEME='https',
    PROXY_FIX_X_FOR=1,
    PROXY_FIX_X_PROTO=1,
    PROXY_FIX_X_HOST=1,
    PROXY_FIX_X_PORT=1,
    PROXY_FIX_X_PREFIX=1
)

# Configuração do SQLAlchemy
server.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/dashboard.db'
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurações de segurança
CORS(server, resources={r"/*": {"origins": "*"}})

# Inicialização do Dash
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

# Configurações do Dash
app.title = "Dashboard Renov"
app.config.suppress_callback_exceptions = True

# Inicializa o SQLAlchemy
db = SQLAlchemy(server)

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
        cpu_status = {
            'value': cpu_percent,
            'status': 'critical' if cpu_percent > 90 else 'warning' if cpu_percent > 70 else 'ok'
        }
        
        # Verifica uso de memória
        memory = psutil.virtual_memory()
        memory_percent = cast(float, memory.percent)
        memory_status = {
            'value': memory_percent,
            'status': 'critical' if memory_percent > 90 else 'warning' if memory_percent > 70 else 'ok'
        }
        
        # Verifica espaço em disco
        disk = psutil.disk_usage('/')
        disk_percent = cast(float, disk.percent)
        disk_status = {
            'value': disk_percent,
            'status': 'critical' if disk_percent > 90 else 'warning' if disk_percent > 70 else 'ok'
        }
        
        # Verifica conexão com o banco de dados
        db_status = {'status': 'ok'}
        try:
            user_db = UserDatabase()
            if not user_db.test_connection():
                db_status = {'status': 'error'}
        except Exception:
            db_status = {'status': 'error'}
        
        # Define o status inicial
        system_status = {
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
        error_status = {
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

# Vincula o servidor Flask ao Dash
app.server = server
app.title = "Dashboard Renov"

# Configurações do Flask para produção/desenvolvimento
# Configurações básicas
server.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(16)),
    FLASK_ENV='production',  # Sempre production em deploy
    DEBUG=False,  # Sempre False em produção
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

# Configuração do SQLAlchemy
app.server.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/dashboard.db'
app.server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o SQLAlchemy com a instância Flask
db.init_app(app.server)

# Inicializa os bancos de dados
db = UserDatabase()
network_db = NetworkDatabase()

# Adiciona endpoint de healthcheck
@server.route('/health')
def health_check():
    health_status = check_system_health()
    
    if health_status['status'] == 'error':
        return jsonify(health_status), 500
    elif health_status['status'] == 'unhealthy':
        return jsonify(health_status), 503
    else:
        return jsonify(health_status), 200

# ========================
# 🔐 Layout Principal
# ========================

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

app.layout = serve_layout

# ========================
# 📊 Layout do Dashboard
# ========================

def create_dashboard_layout(is_super_admin=False):
    """Cria o layout do dashboard"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Img(
                        src='/assets/images/Logo Roxo.png',
                        className="dashboard-logo"
                    ),
                    html.H1("Dashboard de Performance", className="dashboard-title")
                ], className="dashboard-header")
            ], width=10),
            dbc.Col([
                dbc.Button(
                    "Sair",
                    id="logout-button",
                    color="danger",
                    className="mt-2"
                )
            ], width=2)
        ], className="mb-4"),
        
        # Upload Section
        dbc.Row([
            dbc.Col([
                html.H5("📤 Upload de Dados", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Upload(
                            id='upload-data',
                            children=dbc.Button(
                                "Atualizar Base de Resultados",
                                color="primary",
                                className="w-100"
                            ),
                            multiple=False
                        )
                    ], width=4),
                    dbc.Col([
                        dcc.Upload(
                            id='upload-networks-branches-file',
                            children=dbc.Button(
                                "Atualizar Base de Redes e Filiais",
                                color="secondary",
                                className="w-100"
                            ),
                            multiple=False
                        )
                    ], width=4),
                    dbc.Col([
                        dcc.Upload(
                            id='upload-employees-file',
                            children=dbc.Button(
                                "Atualizar Base de Colaboradores",
                                color="secondary",
                                className="w-100"
                            ),
                            multiple=False
                        )
                    ], width=4)
                ], className="mb-3"),
                html.Div([
                    html.Div(id='upload-status'),
                    html.Div(id='network-upload-status')
                ], className="mt-2")
            ], width=12)
        ], className="mb-4"),
        
        # Filtros
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.H5("🔍 Filtros", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Período:", className="filter-label"),
                            dbc.Row([
                                dbc.Col([
                                    dcc.DatePickerSingle(
                                        id='filter-start-date',
                                        placeholder="Data Inicial",
                                        display_format='DD/MM/YYYY'
                                    )
                                ], width=6),
                                dbc.Col([
                                    dcc.DatePickerSingle(
                                        id='filter-end-date',
                                        placeholder="Data Final",
                                        display_format='DD/MM/YYYY'
                                    )
                                ], width=6)
                            ])
                        ], md=3),
                        dbc.Col([
                            html.Label("Mês:", className="filter-label"),
                            dcc.Dropdown(
                                id='filter-month',
                                multi=True,
                                placeholder="Selecione o(s) mês(es)"
                            )
                        ], md=3),
                        dbc.Col([
                            html.Label("Rede:", className="filter-label"),
                            dcc.Dropdown(
                                id='filter-network',
                                multi=True,
                                placeholder="Selecione a(s) rede(s)"
                            )
                        ], md=3),
                        dbc.Col([
                            html.Label("Situação:", className="filter-label"),
                            dcc.Dropdown(
                                id='filter-status',
                                multi=True,
                                placeholder="Selecione a(s) situação(ões)"
                            )
                        ], md=3)
                    ]),
                    dbc.Button(
                        "Limpar Filtros",
                        id="clear-filters",
                        color="secondary",
                        size="sm",
                        className="mt-3"
                    )
                ])
            ])
        ], id='filters-section', style={'display': 'none'}, className="mb-4"),
        
        # Tabs
        dcc.Tabs(
            id="main-tabs",
            value="overview",
            className="custom-tabs",
            children=[
                dcc.Tab(label="Visão Geral", value="overview"),
                dcc.Tab(label="Redes", value="networks"),
                dcc.Tab(label="Tim", value="tim"),
                dcc.Tab(label="Rankings", value="rankings"),
                dcc.Tab(label="Projeções", value="projections"),
                dcc.Tab(label="Engajamento", value="engagement"),
                dcc.Tab(label="Redes e Colaboradores", value="network-employees")
            ]
        ),
        
        # Área de conteúdo
        html.Div(id='tab-content-area', className="mt-4")
    ], fluid=True)

# ========================
# 📊 FUNÇÕES DE GERAÇÃO DE CONTEÚDO
# ========================

def no_data_message():
    return html.Div([
        dbc.Alert([
            html.H4("Nenhum dado disponível", className="alert-heading"),
            html.P("Por favor, faça o upload de um arquivo Excel com os dados para visualização.",
                   className="mb-0")
        ], color="warning", className="mb-3")
    ])

def error_message(message="Ocorreu um erro ao processar os dados."):
    return dbc.Alert(
        message,
        color="danger",
        className="mb-3"
    )

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

def generate_overview_content(df, include_kpis=False):
    """Gera o conteúdo da aba de visão geral"""
    try:
        if df.empty:
            return dbc.Alert("Nenhum dado disponível para análise.", color="warning")
        
        # Gráfico de pizza - distribuição por situação
        status_counts = df['situacao_voucher'].value_counts()
        fig_pie = px.pie(
            values=status_counts.values, 
            names=status_counts.index,
            title="📊 Distribuição por Situação"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        
        # Gráfico de barras - top redes (total)
        network_counts = df['nome_rede'].value_counts().head(10)
        fig_bar_total = px.bar(
            x=network_counts.values,
            y=network_counts.index,
            orientation='h',
            title="🏪 Volume por Rede (Top 10)",
            color=network_counts.values,
            color_continuous_scale='blues'
        )
        fig_bar_total.update_layout(yaxis={'categoryorder': 'total ascending'})
        
        # Gráfico de barras - top redes (apenas utilizados)
        used_vouchers = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        network_used_counts = used_vouchers['nome_rede'].value_counts().head(10)
        fig_bar_used = px.bar(
            x=network_used_counts.values,
            y=network_used_counts.index,
            orientation='h',
            title="✅ Volume por Rede Utilizados (Top 10)",
            color=network_used_counts.values,
            color_continuous_scale='greens'
        )
        fig_bar_used.update_layout(yaxis={'categoryorder': 'total ascending'})
        
        # Gráfico de evolução diária
        if 'data_str' in df.columns:
            daily_series = df.groupby('data_str').size().reset_index(name='count')
            daily_series['data_str'] = pd.to_datetime(daily_series['data_str'])
            
            fig_line = px.line(
                daily_series, 
                x='data_str', 
                y='count',
                title="📅 Evolução Diária de Vouchers"
            )
            fig_line.update_traces(line_color='#3498db')
        else:
            fig_line = go.Figure()
            fig_line.add_annotation(
                text="Dados temporais não disponíveis",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False
            )
        
        return html.Div([
            # Primeira linha: Vouchers utilizados + Gráfico total
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_bar_used)], md=6),
                dbc.Col([dcc.Graph(figure=fig_bar_total)], md=6)
            ], className="mb-4"),
            
            # Segunda linha: Pizza de situações + Evolução temporal
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_pie)], md=6),
                dbc.Col([dcc.Graph(figure=fig_line)], md=6)
            ])
        ])
        
    except Exception as e:
        print(f"Erro na visão geral: {str(e)}")
        traceback.print_exc()
        return dbc.Alert(f"Erro na visão geral: {str(e)}", color="danger")

def generate_networks_content(df):
    """Gera o conteúdo da aba de redes"""
    try:
        if df.empty:
            return dbc.Alert("Nenhum dado disponível para análise.", color="warning")
        
        # Filtrar apenas vouchers utilizados
        df_used = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        
        # Agrupar por rede
        network_summary = df_used.groupby('nome_rede').agg({
            'id': 'count',  # Total de vouchers
            'valor_dispositivo': 'sum'  # Soma do valor dos dispositivos
        }).reset_index()
        
        # Renomear colunas
        network_summary.columns = ['Rede', 'Total de Vouchers', 'Valor Total']
        
        # Ordenar por total de vouchers
        network_summary = network_summary.sort_values('Total de Vouchers', ascending=False)
        
        # Formatar valores monetários
        network_summary['Valor Total'] = network_summary['Valor Total'].apply(
            lambda x: f"R$ {x:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
        )
        
        # Criar tabela
        table = dash_table.DataTable(
            data=network_summary.to_dict('records'),
            columns=[{"name": i, "id": i} for i in network_summary.columns],
            style_header={
                'backgroundColor': '#3498db',
                'color': 'white',
                'fontWeight': 'bold',
                'textAlign': 'center'
            },
            style_cell={
                'textAlign': 'center',
                'padding': '10px'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                }
            ],
            page_size=10,
            sort_action='native'
        )
        
        # Gráficos
        # 1. Volume por Rede
        fig_volume = px.bar(
            network_summary,
            x='Rede',
            y='Total de Vouchers',
            title="📊 Volume por Rede",
            color='Total de Vouchers',
            color_continuous_scale='blues'
        )
        
        # 2. Valor Total por Rede
        network_summary['Valor Numérico'] = df_used.groupby('nome_rede')['valor_dispositivo'].sum().values
        fig_value = px.bar(
            network_summary,
            x='Rede',
            y='Valor Numérico',
            title="💰 Valor Total por Rede",
            color='Valor Numérico',
            color_continuous_scale='greens'
        )
        fig_value.update_layout(
            yaxis_title="Valor Total (R$)",
            yaxis_tickformat=",.2f"
        )
        
        return html.Div([
            # Tabela
            html.H4("📋 Resumo por Rede", className="mb-4"),
            table,
            
            # Gráficos
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_volume)], md=6),
                dbc.Col([dcc.Graph(figure=fig_value)], md=6)
            ], className="mt-4")
        ])
        
    except Exception as e:
        print(f"Erro na aba de redes: {str(e)}")
        traceback.print_exc()
        return dbc.Alert(f"Erro na aba de redes: {str(e)}", color="danger")

def generate_tim_content(df):
    if df is None or df.empty:
        return no_data_message()
    
    try:
        # Filtrar apenas dados da TIM
        df_tim = df[df['nome_rede'].str.upper() == 'TIM']
        
        if df_tim.empty:
            return html.Div([
                html.H4("Dados TIM", className="mb-4"),
                html.P("Nenhum dado encontrado para a rede TIM no período selecionado.")
            ])
        
        # Calcular KPIs da TIM
        total_vouchers = len(df_tim)
        used_vouchers = df_tim[df_tim['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        total_used = len(used_vouchers)
        
        total_value = used_vouchers['valor_dispositivo'].sum()
        avg_ticket = total_value / total_used if total_used > 0 else 0
        conversion_rate = (total_used / total_vouchers * 100) if total_vouchers > 0 else 0
        
        total_stores = df_tim['nome_filial'].nunique()
        active_stores = used_vouchers['nome_filial'].nunique() if not used_vouchers.empty else 0
        
        # KPI Cards
        kpi_cards = dbc.Row([
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
        
        # Gráfico de evolução diária
        if 'data_str' in df_tim.columns:
            daily_series = df_tim.groupby('data_str').size().reset_index(name='count')
            daily_series['data_str'] = pd.to_datetime(daily_series['data_str'])
            
            fig_line = px.line(
                daily_series,
                x='data_str',
                y='count',
                title="📅 Evolução Diária de Vouchers TIM",
                labels={'data_str': 'Data', 'count': 'Quantidade de Vouchers'}
            )
            fig_line.update_traces(line_color='#3498db', line_width=3)
            fig_line.update_layout(height=350)
        else:
            fig_line = go.Figure()
            fig_line.add_annotation(
                text="Dados temporais não disponíveis",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font_size=16
            )
            fig_line.update_layout(height=350, title="Evolução Diária TIM")
        
        # Ranking de lojas TIM
        store_stats = df_tim.groupby('nome_filial').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).round(2)
        store_stats.columns = ['Total_Vouchers', 'Valor_Total']
        store_stats = store_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(10)
        
        return html.Div([
            html.H4("Dashboard TIM", className="mb-4"),
            kpi_cards,
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_line)], md=12)
            ], className="mb-4"),
            html.H5("🏪 Top 10 Lojas TIM", className="mb-3"),
            dash_table.DataTable(
                data=store_stats.to_dict('records'),
                columns=[
                    {"name": "Loja", "id": "nome_filial"},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric", "format": {"specifier": ","}},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.2f", "prefix": "R$ "}}
                ],
                style_cell={"textAlign": "left"},
                style_header={"backgroundColor": "#e74c3c", "color": "white", "fontWeight": "bold"},
                page_size=10,
                sort_action="native"
            )
        ])
    except Exception as e:
        print(f"Erro ao gerar conteúdo TIM: {str(e)}")
        return error_message()

def generate_rankings_content(df):
    """Gera o conteúdo da aba de rankings"""
    try:
        if df.empty:
            return dbc.Alert("Dados não disponíveis para rankings.", color="warning")
        
        # Ranking de lojas
        store_stats = df.groupby(['nome_filial', 'nome_rede']).agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).round(2)
        store_stats.columns = ['Total_Vouchers', 'Valor_Total']
        store_stats = store_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(25)
        
        # Ranking de vendedores
        seller_stats = df.groupby(['nome_vendedor', 'nome_filial', 'nome_rede']).agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).round(2)
        seller_stats.columns = ['Total_Vouchers', 'Valor_Total']
        seller_stats = seller_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(25)
        
        return html.Div([
            html.H5("🏪 Ranking das Lojas (Top 25)", className="mb-3"),
            dash_table.DataTable(
                data=store_stats.to_dict('records'),
                columns=[
                    {"name": "Loja", "id": "nome_filial"},
                    {"name": "Rede", "id": "nome_rede"},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric", "format": {"specifier": ","}},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.2f", "prefix": "R$ "}}
                ],
                style_cell={"textAlign": "left"},
                style_header={"backgroundColor": "#e74c3c", "color": "white", "fontWeight": "bold"},
                page_size=25,
                sort_action="native"
            ),
            
            html.H5("👨‍💼 Ranking dos Vendedores (Top 25)", className="mt-5 mb-3"),
            dash_table.DataTable(
                data=seller_stats.to_dict('records'),
                columns=[
                    {"name": "Vendedor", "id": "nome_vendedor"},
                    {"name": "Loja", "id": "nome_filial"},
                    {"name": "Rede", "id": "nome_rede"},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric", "format": {"specifier": ","}},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.2f", "prefix": "R$ "}}
                ],
                style_cell={"textAlign": "left"},
                style_header={"backgroundColor": "#2980b9", "color": "white", "fontWeight": "bold"},
                page_size=25,
                sort_action="native"
            )
        ])
    except Exception as e:
        return dbc.Alert(f"Erro nos rankings: {str(e)}", color="danger")

def generate_projections_content(df):
    """Gera o conteúdo da aba de projeções"""
    try:
        if df.empty:
            return dbc.Alert("Dados não disponíveis para projeções.", color="warning")
        
        # Dados históricos
        if 'data_str' in df.columns:
            df['data'] = pd.to_datetime(df['data_str'])
            daily_data = df.groupby('data').agg({
                'imei': 'count',
                'valor_dispositivo': 'sum'
            }).reset_index()
            
            # Calcular médias móveis
            daily_data['MA7_vouchers'] = daily_data['imei'].rolling(window=7).mean()
            daily_data['MA30_vouchers'] = daily_data['imei'].rolling(window=30).mean()
            
            # Gráfico de tendência de vouchers
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=daily_data['data'],
                y=daily_data['imei'],
                name='Vouchers Diários',
                mode='lines',
                line=dict(color='#3498db', width=1)
            ))
            fig_trend.add_trace(go.Scatter(
                x=daily_data['data'],
                y=daily_data['MA7_vouchers'],
                name='Média Móvel 7 dias',
                mode='lines',
                line=dict(color='#e74c3c', width=2)
            ))
            fig_trend.add_trace(go.Scatter(
                x=daily_data['data'],
                y=daily_data['MA30_vouchers'],
                name='Média Móvel 30 dias',
                mode='lines',
                line=dict(color='#2ecc71', width=2)
            ))
            fig_trend.update_layout(
                title='📈 Tendência de Vouchers',
                xaxis_title='Data',
                yaxis_title='Quantidade de Vouchers',
                height=400
            )
            
            # Projeção simples
            last_30_avg = daily_data['imei'].tail(30).mean()
            last_7_avg = daily_data['imei'].tail(7).mean()
            
            trend = (last_7_avg - last_30_avg) / last_30_avg * 100
            
            # Estatísticas de projeção
            stats_cards = dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Média Últimos 30 dias", className="card-title text-muted mb-2"),
                            html.H3(f"{last_30_avg:.1f}", className="text-primary fw-bold mb-1"),
                            html.Small("vouchers/dia", className="text-muted")
                        ])
                    ], className="h-100 shadow-sm border-0")
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Média Últimos 7 dias", className="card-title text-muted mb-2"),
                            html.H3(f"{last_7_avg:.1f}", className="text-primary fw-bold mb-1"),
                            html.Small("vouchers/dia", className="text-muted")
                        ])
                    ], className="h-100 shadow-sm border-0")
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Tendência", className="card-title text-muted mb-2"),
                            html.H3([
                                html.I(className=f"fas fa-{'arrow-up' if trend > 0 else 'arrow-down'} me-2"),
                                f"{abs(trend):.1f}%"
                            ], className=f"{'text-success' if trend > 0 else 'text-danger'} fw-bold mb-1"),
                            html.Small("em relação à média de 30 dias", className="text-muted")
                        ])
                    ], className="h-100 shadow-sm border-0")
                ], md=4)
            ], className="g-2 mb-4")
            
            return html.Div([
                html.H4("📊 Análise de Tendências", className="mb-4"),
                stats_cards,
                dcc.Graph(figure=fig_trend),
                html.Hr(),
                html.H5("📝 Observações", className="mb-3"),
                html.Ul([
                    html.Li("As médias móveis ajudam a identificar tendências eliminando ruídos diários"),
                    html.Li("A tendência é calculada comparando as médias de 7 e 30 dias"),
                    html.Li("Valores positivos indicam crescimento, negativos indicam redução")
                ], className="text-muted")
            ])
        else:
            return dbc.Alert(
                "Dados temporais não disponíveis para análise de tendências.",
                color="warning"
            )
            
    except Exception as e:
        print(f"Erro nas projeções: {str(e)}")
        traceback.print_exc()
        return dbc.Alert(f"Erro nas projeções: {str(e)}", color="danger")

def generate_engagement_content(df):
    """Gera o conteúdo da aba de engajamento"""
    try:
        if df.empty:
            return dbc.Alert("Dados não disponíveis para análise de engajamento.", color="warning")
        
        # Métricas por vendedor
        seller_metrics = df.groupby('nome_vendedor').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).reset_index()
        
        # Adicionar média diária (assumindo período de 30 dias)
        seller_metrics['media_diaria'] = seller_metrics['imei'] / 30
        
        # Ordenar por volume
        seller_metrics = seller_metrics.sort_values('imei', ascending=False)
        
        # Calcular quartis para classificação
        q75 = seller_metrics['imei'].quantile(0.75)
        q50 = seller_metrics['imei'].quantile(0.50)
        q25 = seller_metrics['imei'].quantile(0.25)
        
        def get_performance_class(x):
            if x >= q75:
                return 'Alto Desempenho'
            elif x >= q50:
                return 'Acima da Média'
            elif x >= q25:
                return 'Abaixo da Média'
            else:
                return 'Baixo Desempenho'
        
        seller_metrics['classificacao'] = seller_metrics['imei'].apply(get_performance_class)
        
        # Gráfico de distribuição de vendedores
        fig_dist = px.histogram(
            seller_metrics,
            x='imei',
            nbins=20,
            title="📊 Distribuição de Vendedores por Volume",
            labels={'imei': 'Quantidade de Vouchers', 'count': 'Número de Vendedores'}
        )
        fig_dist.add_vline(x=q25, line_dash="dash", line_color="red")
        fig_dist.add_vline(x=q50, line_dash="dash", line_color="yellow")
        fig_dist.add_vline(x=q75, line_dash="dash", line_color="green")
        
        # Gráfico de pizza com classificação
        class_counts = seller_metrics['classificacao'].value_counts()
        fig_pie = px.pie(
            values=class_counts.values,
            names=class_counts.index,
            title="🎯 Distribuição por Nível de Desempenho",
            color=class_counts.index,
            color_discrete_map={
                'Alto Desempenho': '#2ecc71',
                'Acima da Média': '#f1c40f',
                'Abaixo da Média': '#e67e22',
                'Baixo Desempenho': '#e74c3c'
            }
        )
        
        # Tabela de vendedores
        seller_metrics['valor_dispositivo'] = seller_metrics['valor_dispositivo'].round(2)
        seller_metrics['media_diaria'] = seller_metrics['media_diaria'].round(2)
        
        table = dash_table.DataTable(
            data=seller_metrics.to_dict('records'),
            columns=[
                {"name": "Vendedor", "id": "nome_vendedor"},
                {"name": "Total Vouchers", "id": "imei", "type": "numeric", "format": {"specifier": ","}},
                {"name": "Valor Total", "id": "valor_dispositivo", "type": "numeric", "format": {"specifier": ",.2f", "prefix": "R$ "}},
                {"name": "Média Diária", "id": "media_diaria", "type": "numeric", "format": {"specifier": ".1f"}},
                {"name": "Classificação", "id": "classificacao"}
            ],
            style_cell={"textAlign": "left"},
            style_header={
                "backgroundColor": "#3498db",
                "color": "white",
                "fontWeight": "bold"
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{classificacao} = "Alto Desempenho"'},
                    'backgroundColor': '#d5f5e3',
                    'color': '#196f3d'
                },
                {
                    'if': {'filter_query': '{classificacao} = "Acima da Média"'},
                    'backgroundColor': '#fef9e7',
                    'color': '#b7950b'
                },
                {
                    'if': {'filter_query': '{classificacao} = "Abaixo da Média"'},
                    'backgroundColor': '#fbeee6',
                    'color': '#a04000'
                },
                {
                    'if': {'filter_query': '{classificacao} = "Baixo Desempenho"'},
                    'backgroundColor': '#fadbd8',
                    'color': '#943126'
                }
            ],
            page_size=10,
            sort_action="native"
        )
        
        return html.Div([
            html.H4("📈 Análise de Engajamento", className="mb-4"),
            
            # Gráficos
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_dist)], md=8),
                dbc.Col([dcc.Graph(figure=fig_pie)], md=4)
            ], className="mb-4"),
            
            # Legenda
            html.Div([
                html.H5("📝 Classificação de Desempenho", className="mb-3"),
                html.P([
                    html.Span("Alto Desempenho: ", className="fw-bold text-success"),
                    f"Acima do 3º quartil ({q75:.0f}+ vouchers)"
                ]),
                html.P([
                    html.Span("Acima da Média: ", className="fw-bold text-warning"),
                    f"Entre a mediana e o 3º quartil ({q50:.0f} a {q75:.0f} vouchers)"
                ]),
                html.P([
                    html.Span("Abaixo da Média: ", className="fw-bold text-orange"),
                    f"Entre o 1º quartil e a mediana ({q25:.0f} a {q50:.0f} vouchers)"
                ]),
                html.P([
                    html.Span("Baixo Desempenho: ", className="fw-bold text-danger"),
                    f"Abaixo do 1º quartil (menos de {q25:.0f} vouchers)"
                ])
            ], className="mb-4"),
            
            # Tabela
            html.H5("👥 Desempenho Individual", className="mb-3"),
            table
        ])
        
    except Exception as e:
        print(f"Erro no engajamento: {str(e)}")
        traceback.print_exc()
        return dbc.Alert(f"Erro no engajamento: {str(e)}", color="danger")

def generate_network_employees_content(df, network_df=None, employees_df=None):
    """Gera o conteúdo da aba de redes e colaboradores"""
    try:
        if df.empty:
            return dbc.Alert("Dados não disponíveis para análise.", color="warning")
        
        # Análise por rede
        network_stats = df.groupby('nome_rede').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum',
            'nome_filial': 'nunique',
            'nome_vendedor': 'nunique'
        }).reset_index()
        
        network_stats.columns = [
            'Rede', 'Total_Vouchers', 'Valor_Total',
            'Total_Filiais', 'Total_Vendedores'
        ]
        
        # Calcular métricas adicionais
        network_stats['Ticket_Medio'] = network_stats['Valor_Total'] / network_stats['Total_Vouchers']
        network_stats['Vouchers_por_Filial'] = network_stats['Total_Vouchers'] / network_stats['Total_Filiais']
        network_stats['Vouchers_por_Vendedor'] = network_stats['Total_Vouchers'] / network_stats['Total_Vendedores']
        
        # Formatar valores monetários
        network_stats['Valor_Total_Fmt'] = network_stats['Valor_Total'].apply(
            lambda x: f"R$ {x:,.2f}"
        )
        network_stats['Ticket_Medio_Fmt'] = network_stats['Ticket_Medio'].apply(
            lambda x: f"R$ {x:,.2f}"
        )
        
        # Criar tabela principal
        table = dash_table.DataTable(
            data=network_stats.to_dict('records'),
            columns=[
                {"name": "Rede", "id": "Rede"},
                {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric", "format": {"specifier": ","}},
                {"name": "Valor Total", "id": "Valor_Total_Fmt"},
                {"name": "Ticket Médio", "id": "Ticket_Medio_Fmt"},
                {"name": "Total Filiais", "id": "Total_Filiais", "type": "numeric"},
                {"name": "Total Vendedores", "id": "Total_Vendedores", "type": "numeric"},
                {"name": "Vouchers/Filial", "id": "Vouchers_por_Filial", "type": "numeric", "format": {"specifier": ".1f"}},
                {"name": "Vouchers/Vendedor", "id": "Vouchers_por_Vendedor", "type": "numeric", "format": {"specifier": ".1f"}}
            ],
            style_cell={"textAlign": "left"},
            style_header={
                "backgroundColor": "#3498db",
                "color": "white",
                "fontWeight": "bold"
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                }
            ],
            page_size=10,
            sort_action="native"
        )
        
        # Gráficos
        # 1. Distribuição de vouchers por rede
        fig_vouchers = px.bar(
            network_stats,
            x='Rede',
            y='Total_Vouchers',
            title="📊 Distribuição de Vouchers por Rede",
            color='Total_Vouchers',
            color_continuous_scale='blues'
        )
        
        # 2. Distribuição de filiais e vendedores
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Bar(
            name='Filiais',
            x=network_stats['Rede'],
            y=network_stats['Total_Filiais'],
            marker_color='#3498db'
        ))
        fig_dist.add_trace(go.Bar(
            name='Vendedores',
            x=network_stats['Rede'],
            y=network_stats['Total_Vendedores'],
            marker_color='#2ecc71'
        ))
        fig_dist.update_layout(
            title="🏪 Filiais e Vendedores por Rede",
            barmode='group'
        )
        
        # 3. Ticket médio por rede
        fig_ticket = px.bar(
            network_stats,
            x='Rede',
            y='Ticket_Medio',
            title="💰 Ticket Médio por Rede",
            color='Ticket_Medio',
            color_continuous_scale='greens'
        )
        fig_ticket.update_layout(yaxis_tickformat=",.2f")
        
        # 4. Produtividade
        fig_prod = go.Figure()
        fig_prod.add_trace(go.Bar(
            name='Vouchers/Filial',
            x=network_stats['Rede'],
            y=network_stats['Vouchers_por_Filial'],
            marker_color='#e74c3c'
        ))
        fig_prod.add_trace(go.Bar(
            name='Vouchers/Vendedor',
            x=network_stats['Rede'],
            y=network_stats['Vouchers_por_Vendedor'],
            marker_color='#f39c12'
        ))
        fig_prod.update_layout(
            title="📈 Indicadores de Produtividade",
            barmode='group'
        )
        
        return html.Div([
            html.H4("🏢 Análise de Redes e Colaboradores", className="mb-4"),
            
            # Tabela principal
            html.H5("📋 Resumo por Rede", className="mb-3"),
            table,
            
            # Gráficos em grid 2x2
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_vouchers)], md=6),
                dbc.Col([dcc.Graph(figure=fig_dist)], md=6)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_ticket)], md=6),
                dbc.Col([dcc.Graph(figure=fig_prod)], md=6)
            ]),
            
            # Observações
            html.Hr(),
            html.H5("📝 Observações", className="mb-3"),
            html.Ul([
                html.Li("O ticket médio é calculado dividindo o valor total pelo número de vouchers"),
                html.Li("A produtividade por filial e vendedor ajuda a identificar eficiência operacional"),
                html.Li("Redes com alto número de vouchers mas baixa produtividade podem indicar oportunidades de otimização")
            ], className="text-muted")
        ])
        
    except Exception as e:
        print(f"Erro na análise de redes e colaboradores: {str(e)}")
        traceback.print_exc()
        return dbc.Alert(f"Erro na análise de redes e colaboradores: {str(e)}", color="danger")

# ========================
# 🔄 Callbacks
# ========================

@app.callback(
    Output('tab-content-area', 'children'),
    [Input('main-tabs', 'value'),
     Input('store-data', 'data'),
     Input('store-filtered-data', 'data')]
)
def update_tab_content(tab, data, filtered_data):
    """Atualiza o conteúdo da aba selecionada"""
    try:
        # Se não houver dados, mostra mensagem
        if not data:
            return no_data_message()
        
        # Converte os dados do store para DataFrame
        df = pd.DataFrame(data) if data else pd.DataFrame()
        df_filtered = pd.DataFrame(filtered_data) if filtered_data else df
        
        # Retorna o conteúdo apropriado para cada aba
        if tab == 'overview':
            return generate_overview_content(df_filtered)
        elif tab == 'networks':
            return generate_networks_content(df_filtered)
        elif tab == 'tim':
            return generate_tim_content(df_filtered)
        elif tab == 'rankings':
            return generate_rankings_content(df_filtered)
        elif tab == 'projections':
            return generate_projections_content(df_filtered)
        elif tab == 'engagement':
            return generate_engagement_content(df_filtered)
        elif tab == 'network-employees':
            return generate_network_employees_content(df_filtered)
        else:
            return html.Div("Conteúdo não disponível")
            
    except Exception as e:
        print(f"Erro ao atualizar conteúdo da aba: {str(e)}")
        traceback.print_exc()
        return error_message(f"Erro ao carregar conteúdo: {str(e)}")

@app.callback(
    [Output('filters-section', 'style'),
     Output('store-filtered-data', 'data')],
    [Input('store-data', 'data'),
     Input('filter-start-date', 'date'),
     Input('filter-end-date', 'date'),
     Input('filter-month', 'value'),
     Input('filter-network', 'value'),
     Input('filter-status', 'value')]
)
def update_filtered_data(data, start_date, end_date, months, networks, statuses):
    """Atualiza os dados filtrados com base nos filtros selecionados"""
    try:
        # Se não houver dados, esconde os filtros
        if not data:
            return {'display': 'none'}, None
        
        # Converte os dados para DataFrame
        df = pd.DataFrame(data)
        df_filtered = df.copy()
        
        # Aplica os filtros
        if start_date:
            df_filtered = df_filtered[df_filtered['data_str'] >= start_date]
        if end_date:
            df_filtered = df_filtered[df_filtered['data_str'] <= end_date]
        if months:
            if not isinstance(months, list):
                months = [months]
            df_filtered = df_filtered[df_filtered['mes'].isin(months)]
        if networks:
            if not isinstance(networks, list):
                networks = [networks]
            df_filtered = df_filtered[df_filtered['nome_rede'].isin(networks)]
        if statuses:
            if not isinstance(statuses, list):
                statuses = [statuses]
            df_filtered = df_filtered[df_filtered['situacao_voucher'].isin(statuses)]
        
        return {'display': 'block'}, df_filtered.to_dict('records')
        
    except Exception as e:
        print(f"Erro ao filtrar dados: {str(e)}")
        traceback.print_exc()
        return {'display': 'none'}, None

@app.callback(
    [Output('filter-month', 'options'),
     Output('filter-network', 'options'),
     Output('filter-status', 'options')],
    [Input('store-data', 'data')]
)
def update_filter_options(data):
    """Atualiza as opções dos filtros com base nos dados disponíveis"""
    try:
        if not data:
            return [], [], []
        
        df = pd.DataFrame(data)
        
        # Opções para mês
        month_options = [{'label': m, 'value': m} for m in sorted(df['mes'].unique())]
        
        # Opções para rede
        network_options = [{'label': n, 'value': n} for n in sorted(df['nome_rede'].unique())]
        
        # Opções para situação
        status_options = [{'label': s, 'value': s} for s in sorted(df['situacao_voucher'].unique())]
        
        return month_options, network_options, status_options
        
    except Exception as e:
        print(f"Erro ao atualizar opções dos filtros: {str(e)}")
        traceback.print_exc()
        return [], [], []

@app.callback(
    Output('store-data', 'data'),
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_output(contents, filename):
    """Processa o arquivo Excel enviado e atualiza os dados no store"""
    try:
        if contents is None:
            return None
        
        # Decodifica o conteúdo do arquivo
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Lê o arquivo Excel
        df = pd.read_excel(io.BytesIO(decoded))
        
        # Processa as datas
        if 'data' in df.columns:
            df['data_str'] = df['data'].dt.strftime('%Y-%m-%d')
            df['mes'] = df['data'].dt.strftime('%Y-%m')
        
        # Retorna os dados processados
        return df.to_dict('records')
        
    except Exception as e:
        print(f"Erro ao processar arquivo: {str(e)}")
        traceback.print_exc()
        return None

@app.callback(
    Output('clear-filters', 'n_clicks'),
    [Input('clear-filters', 'n_clicks')],
    [State('filter-start-date', 'date'),
     State('filter-end-date', 'date'),
     State('filter-month', 'value'),
     State('filter-network', 'value'),
     State('filter-status', 'value')]
)
def clear_filters(n_clicks, start_date, end_date, months, networks, statuses):
    """Limpa todos os filtros"""
    if n_clicks:
        # Reseta todos os filtros
        return None
    return n_clicks

# Callback para atualizar o status do upload
@app.callback(
    Output('upload-status', 'children'),
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename')]
)
def update_upload_status(contents, filename):
    """Atualiza o status do upload do arquivo"""
    if contents is not None:
        try:
            # Decodifica e processa o arquivo
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.read_excel(io.BytesIO(decoded))
            
            return dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                f"Arquivo '{filename}' carregado com sucesso! ({len(df)} registros)"
            ], color="success", className="mt-2")
            
        except Exception as e:
            return dbc.Alert([
                html.I(className="fas fa-exclamation-circle me-2"),
                f"Erro ao processar arquivo: {str(e)}"
            ], color="danger", className="mt-2")
    return ""

# Callback para atualizar o status do upload de redes e filiais
@app.callback(
    Output('network-upload-status', 'children'),
    [Input('upload-networks-branches-file', 'contents'),
     Input('upload-networks-branches-file', 'filename')]
)
def update_network_upload_status(contents, filename):
    """Atualiza o status do upload do arquivo de redes e filiais"""
    if contents is not None:
        try:
            # Decodifica e processa o arquivo
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.read_excel(io.BytesIO(decoded))
            
            return dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                f"Arquivo '{filename}' carregado com sucesso! ({len(df)} registros)"
            ], color="success", className="mt-2")
            
        except Exception as e:
            return dbc.Alert([
                html.I(className="fas fa-exclamation-circle me-2"),
                f"Erro ao processar arquivo: {str(e)}"
            ], color="danger", className="mt-2")
    return ""

# ========================
# 🔐 Autenticação
# ========================

@app.callback(
    [Output('page-content', 'children'),
     Output('session-store', 'data'),
     Output('auth-status', 'children')],
    [Input('url', 'pathname'),
     Input('login-button', 'n_clicks'),
     Input('logout-button', 'n_clicks')],
    [State('username', 'value'),
     State('password', 'value'),
     State('session-store', 'data')]
)
def manage_auth(pathname, login_clicks, logout_clicks, username, password, session_data):
    """Gerencia a autenticação e navegação do usuário"""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        # Primeira carga da página
        if session_data and session_data.get('authenticated'):
            return create_dashboard_layout(), session_data, ""
        return create_login_layout(), None, ""
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'login-button' and login_clicks:
        if username == 'admin' and password == 'admin':  # Credenciais temporárias
            session_data = {'authenticated': True, 'username': username}
            return create_dashboard_layout(), session_data, ""
        else:
            return create_login_layout(), None, dbc.Alert(
                "Credenciais inválidas. Por favor, tente novamente.",
                color="danger",
                className="mt-3"
            )
    
    elif trigger_id == 'logout-button' and logout_clicks:
        return create_login_layout(), None, ""
    
    elif trigger_id == 'url':
        if session_data and session_data.get('authenticated'):
            return create_dashboard_layout(), session_data, ""
        return create_login_layout(), None, ""
    
    # Fallback
    return create_login_layout(), None, ""

def create_login_layout():
    """Cria o layout da página de login"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Img(
                        src='/assets/images/Logo Roxo.png',
                        className="login-logo mb-4"
                    ),
                    html.H2("Login", className="text-center mb-4"),
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Input(
                                id="username",
                                type="text",
                                placeholder="Usuário",
                                className="mb-3"
                            ),
                            dbc.Input(
                                id="password",
                                type="password",
                                placeholder="Senha",
                                className="mb-4"
                            ),
                            dbc.Button(
                                "Entrar",
                                id="login-button",
                                color="primary",
                                className="w-100"
                            )
                        ])
                    ])
                ], className="login-container")
            ], md=6, className="mx-auto")
        ], className="vh-100 align-items-center")
    ], fluid=True)

# Inicializa o servidor
if __name__ == '__main__':
    # Cria o diretório de dados se não existir
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Inicializa o banco de dados
    db = UserDatabase()
    network_db = NetworkDatabase()
    
    # Inicia o servidor
    app.run_server(
        host=HOST,
        port=PORT,
        debug=False  # Sempre False em produção
    )