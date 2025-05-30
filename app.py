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

def check_system_health() -> SystemStatus:
    """Verifica a saúde do sistema"""
    try:
        # Verifica uso de CPU
        cpu_percent: PercentageValue = cast(float, psutil.cpu_percent(interval=1))
        
        # Verifica uso de memória
        memory = psutil.virtual_memory()
        memory_percent: PercentageValue = cast(float, memory.percent)
        
        # Verifica espaço em disco
        disk = psutil.disk_usage('/')
        disk_percent: PercentageValue = cast(float, disk.percent)
        
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
        
        # Constrói o dicionário de retorno
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
# Em produção, usa a porta fornecida pelo ambiente ou 8080 como fallback
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'  # Sempre usa 0.0.0.0 para aceitar conexões externas

# Inicialização do Flask
server = Flask(__name__)

# Inicialização do Dash com todas as configurações necessárias
app = dash.Dash(
    __name__,
    server=cast(bool, server),
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
        
        # Upload Section with Network Buttons
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        dcc.Upload(
                            id='upload-networks-branches-file',
                            children=dbc.Button(
                                "Atualizar Base de Redes e Filiais",
                                id="upload-networks-branches",
                                color="secondary",
                                size="sm",
                                className="w-100"
                            ),
                            className="me-2"
                        ),
                    ], width=6),
                    dbc.Col([
                        dcc.Upload(
                            id='upload-employees-file',
                            children=dbc.Button(
                                "Atualizar Base de Colaboradores",
                                id="upload-employees",
                                color="secondary",
                                size="sm",
                                className="w-100"
                            ),
                            className="me-2"
                        ),
                    ], width=6),
                ], className="mb-3"),
                html.Div(id='network-upload-status')
            ], width=12),
            dbc.Col([
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        'Arraste e solte ou ',
                        html.A('selecione um arquivo Excel', className="text-primary")
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                    },
                    multiple=False
                ),
                html.Div(id='upload-status')
            ], width=12)
        ]),
        
        # Welcome Message (shown before upload)
        html.Div(id='welcome-message', children=[
            html.H4("👋 Bem-vindo ao Dashboard!", className="text-center mt-5"),
            html.P("Faça o upload de um arquivo Excel para começar.", className="text-center text-muted")
        ]),
        
        # Filters Section (hidden initially)
        html.Div(id='filters-section', style={'display': 'none'}, children=[
            dbc.Row([
                dbc.Col([
                    html.H5("🔍 Filtros", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Mês:"),
                            dcc.Dropdown(id='filter-month', multi=True, placeholder="Selecione o(s) mês(es)")
                        ], md=4),
                        dbc.Col([
                            html.Label("Rede:"),
                            dcc.Dropdown(id='filter-network', multi=True, placeholder="Selecione a(s) rede(s)")
                        ], md=4),
                        dbc.Col([
                            html.Label("Situação:"),
                            dcc.Dropdown(id='filter-status', multi=True, placeholder="Selecione o(s) status")
                        ], md=4)
                    ]),
                    dbc.Button("Limpar Filtros", id="clear-filters", 
                             color="secondary", size="sm", className="mt-2")
                ])
            ], className="mb-4")
        ]),
        
        # KPIs Section
        html.Div(id='kpi-section'),
        
        # Tabs Section (hidden initially)
        html.Div(id='tabs-section', style={'display': 'none'}, children=[
            dcc.Tabs(id='main-tabs', value='overview', children=[
                dcc.Tab(label='Visão Geral', value='overview'),
                dcc.Tab(label='Redes', value='networks'),
                dcc.Tab(label='Rankings', value='rankings'),
                dcc.Tab(label='Projeções', value='projections'),
                dcc.Tab(label='Base de Redes e Colaboradores', value='network-base'),
                dcc.Tab(label='Engajamento', value='engagement')
            ], className="mb-4"),
            html.Div(id='tab-content-area')
        ])
    ], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'padding': '20px'})

# ========================
# 📊 FUNÇÕES DE GERAÇÃO DE CONTEÚDO
# ========================
def generate_kpi_cards(df):
    """Gera cards com KPIs principais"""
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

def generate_overview_content(df):
    """Gera o conteúdo da aba de visão geral"""
    try:
        # Gráfico de pizza - distribuição por situação
        status_counts = df['situacao_voucher'].value_counts()
        fig_pie = px.pie(
            values=status_counts.values, 
            names=status_counts.index,
            title="📊 Distribuição por Situação"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(height=400)
        
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
        fig_bar_total.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
        
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
        fig_bar_used.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
        
        # Gráfico de evolução diária
        if 'data_str' in df.columns:
            daily_series = df.groupby('data_str').size().reset_index(name='count')
            daily_series['data_str'] = pd.to_datetime(daily_series['data_str'])
            
            fig_line = px.line(
                daily_series, 
                x='data_str', 
                y='count',
                title="📅 Evolução Diária de Vouchers",
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
            fig_line.update_layout(height=350, title="Evolução Diária")
        
        # Análise por rede para tabela
        unique_days = df['data_str'].nunique() if 'data_str' in df.columns else 1
        
        network_summary = []
        for rede in df['nome_rede'].unique():
            rede_data = df[df['nome_rede'] == rede]
            rede_used = used_vouchers[used_vouchers['nome_rede'] == rede]
            
            vouchers_totais = len(rede_data)
            vouchers_utilizados = len(rede_used)
            valor_total = rede_used['valor_dispositivo'].sum()
            ticket_medio = valor_total / vouchers_utilizados if vouchers_utilizados > 0 else 0
            lojas_totais = rede_data['nome_filial'].nunique()
            lojas_ativas = rede_used['nome_filial'].nunique() if not rede_used.empty else 0
            
            media_diaria_utilizados = vouchers_utilizados / unique_days if unique_days > 0 else 0
            projecao_mensal_utilizados = media_diaria_utilizados * 30
            projecao_valor_total = (valor_total / unique_days * 30) if unique_days > 0 else 0
            
            network_summary.append({
                'Nome_da_Rede': rede,
                'Vouchers_Totais': int(vouchers_totais),
                'Vouchers_Utilizados': int(vouchers_utilizados),
                'Valor_Total': f"R$ {valor_total:,.0f}",
                'Ticket_Medio': f"R$ {ticket_medio:,.0f}",
                'Lojas_Totais': int(lojas_totais),
                'Lojas_Ativas': int(lojas_ativas),
                'Media_Diaria_Utilizados': round(media_diaria_utilizados, 0),
                'Projecao_Mensal_Utilizados': int(projecao_mensal_utilizados),
                'Projecao_Valor_Total': f"R$ {projecao_valor_total:,.0f}"
            })
        
        # Ordenar por vouchers utilizados
        network_summary = sorted(network_summary, key=lambda x: int(x['Vouchers_Utilizados']), reverse=True)
        
        # Tabela com formatação
        network_table = dash_table.DataTable(
            data=network_summary,
            columns=[
                {"name": "Rede", "id": "Nome_da_Rede"},
                {"name": "Vouchers Totais", "id": "Vouchers_Totais", "type": "numeric"},
                {"name": "Vouchers Utilizados", "id": "Vouchers_Utilizados", "type": "numeric"},
                {"name": "Valor Total", "id": "Valor_Total"},
                {"name": "Ticket Médio", "id": "Ticket_Medio"},
                {"name": "Lojas Totais", "id": "Lojas_Totais", "type": "numeric"},
                {"name": "Lojas Ativas", "id": "Lojas_Ativas", "type": "numeric"},
                {"name": "Média Diária Utilizados", "id": "Media_Diaria_Utilizados", "type": "numeric"},
                {"name": "Projeção Mensal Utilizados", "id": "Projecao_Mensal_Utilizados", "type": "numeric"},
                {"name": "Projeção Valor Total", "id": "Projecao_Valor_Total"}
            ],
            style_cell={"textAlign": "left", "fontSize": "11px", "padding": "8px"},
            style_header={"backgroundColor": "#3498db", "color": "white", "fontWeight": "bold"},
            style_data_conditional=[
                {
                    "if": {"row_index": 0},
                    "backgroundColor": "#e8f5e8",
                    "color": "black"
                }
            ],
            sort_action="native",
            page_size=15
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
            ], className="mb-4"),
            
            # Tabela resumo das redes
            html.Hr(),
            html.H5("📋 Resumo Detalhado por Rede", className="mb-3"),
            html.P(f"Análise baseada em {unique_days} dias de dados", className="text-muted mb-3"),
            network_table
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro na visão geral: {str(e)}", color="danger")

def generate_networks_content(df):
    """Gera o conteúdo da aba de redes"""
    try:
        if df.empty or 'nome_rede' not in df.columns:
            return dbc.Alert("Dados de redes não disponíveis.", color="warning")
        
        network_analysis = df.groupby('nome_rede').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum',
            'nome_filial': 'nunique'
        }).round(2)
        network_analysis.columns = ['Total_Vouchers', 'Valor_Total', 'Num_Lojas']
        network_analysis = network_analysis.reset_index()
        
        fig_scatter = px.scatter(
            network_analysis,
            x='Total_Vouchers',
            y='Valor_Total',
            size='Num_Lojas',
            hover_name='nome_rede',
            title="💰 Performance das Redes",
            labels={
                'Total_Vouchers': 'Total de Vouchers',
                'Valor_Total': 'Valor Total (R$)',
                'Num_Lojas': 'Número de Lojas'
            },
            color='Total_Vouchers',
            color_continuous_scale='viridis'
        )
        fig_scatter.update_layout(
            height=500,
            xaxis_title="Total de Vouchers",
            yaxis_title="Valor Total (R$)",
            legend_title="Número de Lojas"
        )
        
        return dbc.Row([
            dbc.Col([dcc.Graph(figure=fig_scatter)], md=12)
        ])
    except Exception as e:
        return dbc.Alert(f"Erro na análise de redes: {str(e)}", color="danger")

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

def generate_projections_content(original_df, filtered_df):
    """Gera o conteúdo da aba de projeções"""
    try:
        if original_df.empty or 'criado_em' not in original_df.columns:
            return dbc.Alert("Dados insuficientes para projeções.", color="warning")
        
        df = original_df.copy()
        df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
        df = df.dropna(subset=['criado_em'])
        
        if df.empty:
            return dbc.Alert("Nenhuma data válida encontrada.", color="warning")
        
        last_date = df['criado_em'].max()
        current_month = last_date.month
        current_year = last_date.year
        
        current_month_data = df[
            (df['criado_em'].dt.month == current_month) & 
            (df['criado_em'].dt.year == current_year)
        ]
        
        used_vouchers_month = current_month_data[current_month_data['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        
        unique_days_month = current_month_data['data_str'].nunique() if 'data_str' in current_month_data.columns else 1
        days_in_month = pd.Timestamp(current_year, current_month, 1).days_in_month
        
        vouchers_totais_mes = len(current_month_data)
        vouchers_utilizados_mes = len(used_vouchers_month)
        valor_total_utilizados = used_vouchers_month['valor_dispositivo'].sum() if 'valor_dispositivo' in used_vouchers_month.columns else 0
        ticket_medio_atual = valor_total_utilizados / vouchers_utilizados_mes if vouchers_utilizados_mes > 0 else 0
        
        media_diaria_totais = vouchers_totais_mes / unique_days_month if unique_days_month > 0 else 0
        media_diaria_utilizados = vouchers_utilizados_mes / unique_days_month if unique_days_month > 0 else 0
        media_diaria_valor = valor_total_utilizados / unique_days_month if unique_days_month > 0 else 0
        
        projecao_vouchers_totais = media_diaria_totais * days_in_month
        projecao_vouchers_utilizados = media_diaria_utilizados * days_in_month
        projecao_valor_total = media_diaria_valor * days_in_month
        projecao_ticket_medio = projecao_valor_total / projecao_vouchers_utilizados if projecao_vouchers_utilizados > 0 else 0
        
        metrics_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("📊 Vouchers Totais", className="mb-0 text-center")),
                    dbc.CardBody([
                        html.Div([
                            html.H5("Atual:", className="text-muted mb-1"),
                            html.H4(f"{vouchers_totais_mes:,}", className="text-info mb-2"),
                            html.H6("Média Diária:", className="text-muted mb-1"),
                            html.H5(f"{media_diaria_totais:.1f}", className="text-primary mb-2"),
                            html.H6("Projeção Mensal:", className="text-muted mb-1"),
                            html.H4(f"{projecao_vouchers_totais:.0f}", className="text-success")
                        ], className="text-center")
                    ])
                ], className="h-100 shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("✅ Vouchers Utilizados", className="mb-0 text-center")),
                    dbc.CardBody([
                        html.Div([
                            html.H5("Atual:", className="text-muted mb-1"),
                            html.H4(f"{vouchers_utilizados_mes:,}", className="text-info mb-2"),
                            html.H6("Média Diária:", className="text-muted mb-1"),
                            html.H5(f"{media_diaria_utilizados:.1f}", className="text-primary mb-2"),
                            html.H6("Projeção Mensal:", className="text-muted mb-1"),
                            html.H4(f"{projecao_vouchers_utilizados:.0f}", className="text-success")
                        ], className="text-center")
                    ])
                ], className="h-100 shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("💰 Valor Total", className="mb-0 text-center")),
                    dbc.CardBody([
                        html.Div([
                            html.H5("Atual:", className="text-muted mb-1"),
                            html.H4(f"R$ {valor_total_utilizados:,.0f}", className="text-info mb-2"),
                            html.H6("Média Diária:", className="text-muted mb-1"),
                            html.H5(f"R$ {media_diaria_valor:,.0f}", className="text-primary mb-2"),
                            html.H6("Projeção Mensal:", className="text-muted mb-1"),
                            html.H4(f"R$ {projecao_valor_total:,.0f}", className="text-success")
                        ], className="text-center")
                    ])
                ], className="h-100 shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("🎯 Ticket Médio", className="mb-0 text-center")),
                    dbc.CardBody([
                        html.Div([
                            html.H5("Atual:", className="text-muted mb-1"),
                            html.H4(f"R$ {ticket_medio_atual:,.2f}", className="text-info mb-2"),
                            html.H6("Meta Diária:", className="text-muted mb-1"),
                            html.H5(f"R$ {ticket_medio_atual:,.2f}", className="text-primary mb-2"),
                            html.H6("Projeção Mensal:", className="text-muted mb-1"),
                            html.H4(f"R$ {projecao_ticket_medio:,.2f}", className="text-success")
                        ], className="text-center")
                    ])
                ], className="h-100 shadow-sm")
            ], md=3)
        ], className="mb-4")
        
        # Gráfico de tendência mensal
        daily_data = df.groupby('data_str').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).reset_index()
        daily_data.columns = ['data', 'vouchers', 'valor']
        daily_data['data'] = pd.to_datetime(daily_data['data'])
        daily_data = daily_data.sort_values('data')
        
        # Criar gráfico de tendência
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=daily_data['data'], 
            y=daily_data['vouchers'],
            mode='lines+markers',
            name='Vouchers',
            line=dict(color='#3498db', width=2),
            marker=dict(size=6)
        ))
        
        fig_trend.update_layout(
            title='📈 Tendência de Vouchers por Dia',
            xaxis_title='Data',
            yaxis_title='Quantidade de Vouchers',
            height=400,
            hovermode='x unified',
            template='plotly_white'
        )
        
        return html.Div([
            html.H4("🔮 Projeções e Análise Detalhada", className="mb-4"),
            html.P(f"Período analisado: {unique_days_month} dias de {pd.Timestamp(current_year, current_month, 1).strftime('%B %Y')}", 
                   className="text-muted mb-4"),
            metrics_cards,
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_trend)], md=12)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("📊 Análise de Projeção", className="mb-0")),
                        dbc.CardBody([
                            html.P([
                                "Com base nos ", html.Strong(f"{unique_days_month}"), " dias analisados no período, ",
                                "a projeção de fechamento mensal indica um total de ", 
                                html.Strong(f"{projecao_vouchers_utilizados:.0f}"), " vouchers utilizados, ",
                                "gerando uma receita projetada de ", 
                                html.Strong(f"R$ {projecao_valor_total:,.2f}"), "."
                            ]),
                            html.P([
                                "O ticket médio projetado é de ", 
                                html.Strong(f"R$ {projecao_ticket_medio:,.2f}"), " por voucher utilizado."
                            ]),
                            html.Hr(),
                            html.P("Esta projeção considera o padrão atual de utilização e pode variar de acordo com ações de marketing, sazonalidade ou outros fatores externos.", className="text-muted")
                        ])
                    ])
                ], md=12)
            ])
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro nas projeções: {str(e)}", color="danger")

def generate_network_base_content():
    """Gera o conteúdo da aba de Base de Redes e Colaboradores"""
    print("\n=== Gerando conteúdo da base de redes ===")
    try:
        db = NetworkDatabase()
        stats = db.get_network_stats()
        
        print("Estatísticas para exibição:")
        print(stats)
        
        if all(v == 0 for v in stats.values()):
            print("Nenhum dado encontrado nas estatísticas")
            return dbc.Alert([
                html.H4("📝 Nenhum dado encontrado", className="alert-heading"),
                html.P([
                    "Para começar, faça o upload dos arquivos de redes/filiais e colaboradores usando os botões acima. ",
                    "Consulte o arquivo GLOSSARIO.md para entender a estrutura dos dados."
                ], className="mb-0"),
                html.Hr(),
                html.P([
                    "Estrutura necessária:",
                    html.Ul([
                        html.Li("Redes e Filiais: Nome da Rede, Nome da Filial, Data de Início"),
                        html.Li("Colaboradores: Nome, Filial, Rede, Status Ativo, Data de Cadastro")
                    ])
                ], className="mb-0")
            ], color="info")
        
        # KPIs principais
        kpi_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("🏢 Total de Redes", className="card-title text-center"),
                        html.H2(f"{stats['total_networks']:,}", 
                               className="text-primary text-center display-4"),
                        html.P("Redes parceiras ativas", className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("🏪 Total de Filiais", className="card-title text-center"),
                        html.H2(f"{stats['total_branches']:,}", 
                               className="text-success text-center display-4"),
                        html.P("Filiais ativas no sistema", className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("👥 Total de Colaboradores", className="card-title text-center"),
                        html.H2(f"{stats['total_employees']:,}", 
                               className="text-info text-center display-4"),
                        html.P("Colaboradores ativos", className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=4)
        ])
        
        # Gráficos evolutivos
        evolution_data = db.get_evolution_data()
        if not evolution_data.empty:
            # Gráfico de evolução de redes
            max_redes = evolution_data['total_redes'].max()
            fig_networks = go.Figure()
            fig_networks.add_trace(go.Bar(
                x=evolution_data['mes'],
                y=evolution_data['total_redes'],
                name='Total de Redes',
                marker_color='#3498db',
                text=evolution_data['total_redes'],
                textposition='outside'
            ))
            fig_networks.update_layout(
                title='Evolução Mensal - Total de Redes Ativas',
                xaxis_title='Mês',
                yaxis_title='Total de Redes',
                height=400,
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis=dict(showgrid=False),
                yaxis=dict(
                    showgrid=False,
                    range=[0, max_redes * 1.15]  # Adiciona 15% de espaço superior
                )
            )
            
            # Gráfico de evolução de filiais
            max_filiais = evolution_data['total_filiais'].max()
            fig_branches = go.Figure()
            fig_branches.add_trace(go.Bar(
                x=evolution_data['mes'],
                y=evolution_data['total_filiais'],
                name='Total de Filiais',
                marker_color='#2ecc71',
                text=evolution_data['total_filiais'],
                textposition='outside'
            ))
            fig_branches.update_layout(
                title='Evolução Mensal - Total de Filiais Ativas',
                xaxis_title='Mês',
                yaxis_title='Total de Filiais',
                height=400,
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis=dict(showgrid=False),
                yaxis=dict(
                    showgrid=False,
                    range=[0, max_filiais * 1.15]  # Adiciona 15% de espaço superior
                )
            )
            
            # Gráfico de evolução de colaboradores
            max_colaboradores = evolution_data['total_colaboradores'].max()
            fig_employees = go.Figure()
            fig_employees.add_trace(go.Bar(
                x=evolution_data['mes'],
                y=evolution_data['total_colaboradores'],
                name='Total de Colaboradores',
                marker_color='#9b59b6',
                text=evolution_data['total_colaboradores'],
                textposition='outside'
            ))
            fig_employees.update_layout(
                title='Evolução Mensal - Total de Colaboradores Ativos',
                xaxis_title='Mês',
                yaxis_title='Total de Colaboradores',
                height=400,
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis=dict(showgrid=False),
                yaxis=dict(
                    showgrid=False,
                    range=[0, max_colaboradores * 1.15]  # Adiciona 15% de espaço superior
                )
            )
            
            evolution_graphs = dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_networks)], md=4),
                dbc.Col([dcc.Graph(figure=fig_branches)], md=4),
                dbc.Col([dcc.Graph(figure=fig_employees)], md=4)
            ], className="mb-4")
        else:
            evolution_graphs = html.Div()
        
        # Tabela de resumo executivo
        executive_summary = db.get_executive_summary()
        if not executive_summary.empty:
            summary_table = dash_table.DataTable(
                data=executive_summary.to_dict('records'),
                columns=[{"name": i, "id": i} for i in executive_summary.columns],
                style_header={
                    'backgroundColor': '#3498db',
                    'color': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_cell={
                    'textAlign': 'center',
                    'padding': '10px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f9f9f9'
                    }
                ],
                page_size=10,
                sort_action='native'
            )
        else:
            summary_table = html.Div()
        
        return html.Div([
            # KPIs
            kpi_cards,
            
            # Gráficos evolutivos
            html.H4("📈 Evolução Mensal", className="mt-4 mb-3"),
            evolution_graphs,
            
            # Resumo executivo
            html.H4("📊 Resumo Executivo por Rede", className="mt-4 mb-3"),
            html.Div([
                summary_table
            ], className="table-responsive")
        ])
        
    except Exception as e:
        print(f"Erro ao gerar conteúdo: {str(e)}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Erro ao carregar estatísticas: {str(e)}", color="danger")

def generate_engagement_content(df, network_db):
    """Gera o conteúdo da aba de Engajamento"""
    try:
        if df.empty:
            return dbc.Alert("Dados não disponíveis para análise de engajamento.", color="warning")

        # Obter dados das bases de redes e colaboradores
        executive_summary = network_db.get_executive_summary()
        
        # Calcular métricas de engajamento considerando apenas os dados filtrados
        total_redes = executive_summary['Nome da Rede'].nunique()
        total_filiais = executive_summary['Total de Filiais'].sum()
        total_colaboradores = executive_summary['Total de Colaboradores'].sum()
        
        # Calcular métricas de vouchers utilizados com base nos dados filtrados
        vouchers_utilizados = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        
        redes_ativas = df['nome_rede'].nunique()
        filiais_ativas = df['nome_filial'].nunique()
        colaboradores_ativos = df['nome_vendedor'].nunique()
        colaboradores_com_vouchers_utilizados = vouchers_utilizados['nome_vendedor'].nunique()
        
        # Análise de inatividade considerando os dados filtrados
        if 'data_str' in df.columns:
            df['data_str'] = pd.to_datetime(df['data_str'])
            ultima_data = df['data_str'].max()
            dias_inatividade = 30
            data_corte = ultima_data - pd.Timedelta(days=dias_inatividade)
            
            colaboradores_ativos_periodo = df[df['data_str'] > data_corte]['nome_vendedor'].unique()
            total_colaboradores_inativos = total_colaboradores - len(colaboradores_ativos_periodo)
            taxa_ausencia_vouchers = (total_colaboradores_inativos / total_colaboradores * 100) if total_colaboradores > 0 else 0
        else:
            taxa_ausencia_vouchers = 0
        
        # Calcular taxas de ativação com base nos dados filtrados
        taxa_ativacao_redes = (redes_ativas / total_redes * 100) if total_redes > 0 else 0
        taxa_ativacao_filiais = (filiais_ativas / total_filiais * 100) if total_filiais > 0 else 0
        taxa_ativacao_colaboradores = (colaboradores_ativos / total_colaboradores * 100) if total_colaboradores > 0 else 0
        taxa_ativacao_colaboradores_utilizados = (colaboradores_com_vouchers_utilizados / total_colaboradores * 100) if total_colaboradores > 0 else 0

        # KPIs de Engajamento
        kpi_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("🎯 Taxa de Ativação de Redes", className="card-title text-center"),
                        html.H2(f"{taxa_ativacao_redes:.1f}%", 
                               className="text-primary text-center display-4"),
                        html.P(f"{redes_ativas} de {total_redes} redes ativas", 
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("🏪 Taxa de Ativação de Filiais", className="card-title text-center"),
                        html.H2(f"{taxa_ativacao_filiais:.1f}%", 
                               className="text-success text-center display-4"),
                        html.P(f"{filiais_ativas} de {total_filiais} filiais ativas", 
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("👥 Taxa de Ativação - Vouchers Utilizados", className="card-title text-center"),
                        html.H2(f"{taxa_ativacao_colaboradores_utilizados:.1f}%", 
                               className="text-info text-center display-4"),
                        html.P(f"{colaboradores_com_vouchers_utilizados} de {total_colaboradores} colaboradores", 
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("⚠️ Taxa de Ausência de Vouchers", className="card-title text-center"),
                        html.H2(f"{taxa_ausencia_vouchers:.1f}%", 
                               className="text-danger text-center display-4"),
                        html.P(f"{total_colaboradores_inativos} colaboradores sem atividade", 
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=3)
        ])

        # Análise Temporal de Engajamento com novo gráfico de colunas empilhadas
        if 'data_str' in df.columns:
            df_temporal = df.groupby('data_str').agg({
                'imei': 'count',  # Total de vouchers gerados
                'nome_vendedor': 'nunique'
            }).reset_index()
            
            # Adicionar contagem de vouchers utilizados
            df_temporal['vouchers_utilizados'] = df[
                df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)
            ].groupby('data_str').size().reindex(df_temporal['data_str']).fillna(0)
            
            df_temporal.columns = ['Data', 'Vouchers_Gerados', 'Colaboradores_Ativos', 'Vouchers_Utilizados']
            df_temporal['Data'] = pd.to_datetime(df_temporal['Data'])
            df_temporal = df_temporal.sort_values('Data')
            
            # Criar gráfico de colunas empilhadas
            fig_temporal = go.Figure()
            
            # Adicionar barras para vouchers gerados (total)
            fig_temporal.add_trace(go.Bar(
                x=df_temporal['Data'],
                y=df_temporal['Vouchers_Gerados'],
                name='Vouchers Gerados',
                marker_color='#3498db'
            ))
            
            # Adicionar barras para vouchers utilizados (sobreposto)
            fig_temporal.add_trace(go.Bar(
                x=df_temporal['Data'],
                y=df_temporal['Vouchers_Utilizados'],
                name='Vouchers Utilizados',
                marker_color='#2ecc71'
            ))
            
            fig_temporal.update_layout(
                title='Evolução Diária de Vouchers',
                xaxis_title='Data',
                yaxis_title='Quantidade',
                barmode='overlay',
                bargap=0.1,
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis=dict(
                    showgrid=False,
                    type='date',
                    tickformat='%d/%m'
                ),
                yaxis=dict(showgrid=False),
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=0.99
                )
            )
            
            # Ajustar opacidade para visualizar as barras sobrepostas
            fig_temporal.update_traces(opacity=0.7)
        
        # Análise de Produtividade por Rede
        prod_rede = df.groupby('nome_rede').agg({
            'imei': 'count',
            'nome_vendedor': 'nunique',
            'valor_dispositivo': 'sum'
        }).reset_index()
        prod_rede.columns = ['Rede', 'Total_Vouchers', 'Total_Colaboradores', 'Valor_Total']
        prod_rede['Media_Vouchers_Colaborador'] = (prod_rede['Total_Vouchers'] / prod_rede['Total_Colaboradores']).round(2)
        prod_rede['Media_Valor_Colaborador'] = (prod_rede['Valor_Total'] / prod_rede['Total_Colaboradores']).round(2)
        
        # Gráfico de produtividade
        fig_produtividade = go.Figure()
        fig_produtividade.add_trace(go.Bar(
            x=prod_rede.head(10)['Rede'],
            y=prod_rede.head(10)['Media_Vouchers_Colaborador'],
            name='Média de Vouchers',
            marker_color='#3498db',
            text=prod_rede.head(10)['Media_Vouchers_Colaborador'].apply(lambda x: f'{x:.1f}'),
            textposition='outside'
        ))
        fig_produtividade.update_layout(
            title='Média de Vouchers por Colaborador (Top 10 Redes)',
            xaxis_title='Rede',
            yaxis_title='Média de Vouchers',
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(showgrid=False),
            yaxis=dict(
                showgrid=False,
                range=[0, max(prod_rede['Media_Vouchers_Colaborador']) * 1.15]
            )
        )

        # Tabela Analítica
        tabela_analitica = []
        for rede in executive_summary['Nome da Rede'].unique():
            rede_data = {
                'Rede': rede,
                'Quantidade_Lojas_Total': executive_summary[executive_summary['Nome da Rede'] == rede]['Total de Filiais'].iloc[0],
                'Quantidade_Lojas_Com_Vouchers': len(df[df['nome_rede'] == rede]['nome_filial'].unique()),
                'Total_Colaboradores_Ativos': executive_summary[executive_summary['Nome da Rede'] == rede]['Total de Colaboradores'].iloc[0],
                'Total_Colaboradores_Com_Vouchers': len(df[df['nome_rede'] == rede]['nome_vendedor'].unique()),
            }
            
            # Calcular campos derivados
            rede_data['Quantidade_Lojas_Sem_Vouchers'] = rede_data['Quantidade_Lojas_Total'] - rede_data['Quantidade_Lojas_Com_Vouchers']
            rede_data['Total_Colaboradores_Sem_Vouchers'] = rede_data['Total_Colaboradores_Ativos'] - rede_data['Total_Colaboradores_Com_Vouchers']
            
            # Calcular taxas
            rede_data['Taxa_Ativacao_Rede'] = f"{(1 if rede_data['Quantidade_Lojas_Com_Vouchers'] > 0 else 0) * 100:.1f}%"
            rede_data['Taxa_Ativacao_Filiais'] = f"{(rede_data['Quantidade_Lojas_Com_Vouchers'] / rede_data['Quantidade_Lojas_Total'] * 100 if rede_data['Quantidade_Lojas_Total'] > 0 else 0):.1f}%"
            rede_data['Taxa_Ativacao_Colaboradores'] = f"{(rede_data['Total_Colaboradores_Com_Vouchers'] / rede_data['Total_Colaboradores_Ativos'] * 100 if rede_data['Total_Colaboradores_Ativos'] > 0 else 0):.1f}%"
            rede_data['Taxa_Ausencia_Vouchers'] = f"{(rede_data['Total_Colaboradores_Sem_Vouchers'] / rede_data['Total_Colaboradores_Ativos'] * 100 if rede_data['Total_Colaboradores_Ativos'] > 0 else 0):.1f}%"
            
            tabela_analitica.append(rede_data)

        # Nova seção: Engajamento de Equipes
        # Preparar dados para a análise de engajamento
        colaboradores_ativos = set(df['nome_vendedor'].unique())
        
        # Obter todos os colaboradores do banco de dados
        todos_colaboradores = network_db.get_all_employees()
        if todos_colaboradores.empty:
            return dbc.Alert("Dados de colaboradores não disponíveis.", color="warning")
        
        # Criar dropdown de redes
        redes_options = [
            {'label': 'Todas as Redes', 'value': 'todas'}
        ] + [
            {'label': rede, 'value': rede}
            for rede in sorted(todos_colaboradores['rede'].unique())
        ]
        
        # Criar dropdown de situação
        situacao_options = [
            {'label': 'Total', 'value': 'total'},
            {'label': 'Utilizado', 'value': 'utilizado'},
            {'label': 'Sem vouchers', 'value': 'sem_vouchers'}
        ]
        
        # Seção de filtros
        filtros_equipes = dbc.Card([
            dbc.CardHeader(html.H5("🎯 Engajamento de Equipes", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Rede:", className="mb-2"),
                        dcc.Dropdown(
                            id='filtro-rede-equipes',
                            options=redes_options,
                            value='todas',
                            clearable=False,
                            className="mb-3"
                        )
                    ], md=5),
                    dbc.Col([
                        html.Label("Situação:", className="mb-2"),
                        dcc.Dropdown(
                            id='filtro-situacao-equipes',
                            options=situacao_options,
                            value='total',
                            clearable=False,
                            className="mb-3"
                        )
                    ], md=5),
                    dbc.Col([
                        html.Label("\u00A0", className="mb-2 d-block"),  # Espaço em branco para alinhar com os dropdowns
                        dbc.Button(
                            [html.I(className="fas fa-file-excel me-2"), "Exportar para Excel"],
                            id="btn-export-excel",
                            color="success",
                            className="w-100"
                        ),
                        dcc.Download(id="download-excel")
                    ], md=2)
                ]),
                html.Div(id='tabela-equipes-container')
            ])
        ], className="mb-4")
        
        # Layout final
        return html.Div([
            # KPIs existentes
            kpi_cards,
            
            # Gráficos existentes
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_temporal)], md=6),
                dbc.Col([dcc.Graph(figure=fig_produtividade)], md=6)
            ], className="mb-4"),
            
            # Nova seção de Engajamento de Equipes
            filtros_equipes,
            
            # Tabela Analítica existente
            html.H5("📋 Análise Detalhada por Rede", className="mt-4 mb-3"),
            dash_table.DataTable(
                data=tabela_analitica,
                columns=[
                    {"name": "Rede", "id": "Rede"},
                    {"name": "Total de Lojas", "id": "Quantidade_Lojas_Total"},
                    {"name": "Lojas com Vouchers", "id": "Quantidade_Lojas_Com_Vouchers"},
                    {"name": "Lojas sem Vouchers", "id": "Quantidade_Lojas_Sem_Vouchers"},
                    {"name": "Total Colaboradores", "id": "Total_Colaboradores_Ativos"},
                    {"name": "Colaboradores com Vouchers", "id": "Total_Colaboradores_Com_Vouchers"},
                    {"name": "Colaboradores sem Vouchers", "id": "Total_Colaboradores_Sem_Vouchers"},
                    {"name": "Taxa Ativação Rede", "id": "Taxa_Ativacao_Rede"},
                    {"name": "Taxa Ativação Filiais", "id": "Taxa_Ativacao_Filiais"},
                    {"name": "Taxa Ativação Colaboradores", "id": "Taxa_Ativacao_Colaboradores"},
                    {"name": "Taxa Ausência Vouchers", "id": "Taxa_Ausencia_Vouchers"}
                ],
                style_header={
                    'backgroundColor': '#3498db',
                    'color': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_cell={
                    'textAlign': 'center',
                    'padding': '10px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f9f9f9'
                    }
                ],
                page_size=10,
                sort_action='native'
            )
        ])
        
    except Exception as e:
        print(f"Erro na análise de engajamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Erro ao gerar análise de engajamento: {str(e)}", color="danger")

@app.callback(
    Output('tabela-equipes-container', 'children'),
    [Input('filtro-rede-equipes', 'value'),
     Input('filtro-situacao-equipes', 'value')],
    [State('store-data', 'data')]
)
def update_tabela_equipes(rede_selecionada, situacao_selecionada, data):
    """Atualiza a tabela de equipes baseada nos filtros selecionados"""
    if not data:
        return html.Div("Nenhum dado disponível.")
    
    try:
        # Converter dados para DataFrame
        df = pd.DataFrame(data)
        
        # Obter dados do banco de dados de redes
        network_db = NetworkDatabase()
        todos_colaboradores = network_db.get_all_employees()
        
        if todos_colaboradores.empty:
            return html.Div("Dados de colaboradores não disponíveis.")
        
        # Filtrar por rede se necessário
        if rede_selecionada and rede_selecionada != 'todas':
            todos_colaboradores = todos_colaboradores[todos_colaboradores['rede'] == rede_selecionada]
        
        # Criar conjunto de colaboradores com vouchers utilizados
        colaboradores_com_vouchers = set(df[
            df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)
        ]['nome_vendedor'].unique())
        
        # Filtrar colaboradores baseado na situação selecionada
        if situacao_selecionada == 'utilizado':
            colaboradores_filtrados = todos_colaboradores[
                todos_colaboradores['nome'].isin(colaboradores_com_vouchers)
            ]
        elif situacao_selecionada == 'sem_vouchers':
            colaboradores_filtrados = todos_colaboradores[
                ~todos_colaboradores['nome'].isin(colaboradores_com_vouchers)
            ]
        else:  # total
            colaboradores_filtrados = todos_colaboradores
        
        # Criar lista de tabelas, uma para cada filial
        tabelas_filiais = []
        for (filial, rede), grupo in colaboradores_filtrados.groupby(['filial', 'rede']):
            # Cabeçalho da filial
            header = dbc.Alert(
                f"📍 {filial} - {rede}",
                color="info",
                className="mt-3 mb-2"
            )
            
            # Preparar dados da tabela
            dados_tabela = []
            total_gerados = 0
            total_utilizados = 0
            
            for _, row in grupo.iterrows():
                vouchers_gerados = len(df[df['nome_vendedor'] == row['nome']])
                vouchers_utilizados = len(df[
                    (df['nome_vendedor'] == row['nome']) & 
                    (df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False))
                ])
                
                total_gerados += vouchers_gerados
                total_utilizados += vouchers_utilizados
                
                dados_tabela.append({
                    'Colaborador': row['nome'],
                    'Vouchers Gerados': vouchers_gerados,
                    'Vouchers Utilizados': vouchers_utilizados
                })
            
            # Adicionar linha de total
            dados_tabela.append({
                'Colaborador': 'Total',
                'Vouchers Gerados': total_gerados,
                'Vouchers Utilizados': total_utilizados
            })
            
            # Tabela de colaboradores da filial
            tabela = dash_table.DataTable(
                data=dados_tabela,
                columns=[
                    {"name": "Colaborador", "id": "Colaborador"},
                    {"name": "Vouchers Gerados", "id": "Vouchers Gerados"},
                    {"name": "Vouchers Utilizados", "id": "Vouchers Utilizados"}
                ],
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'border': '1px solid #dee2e6'
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'border': '1px solid #dee2e6'
                },
                style_table={
                    'border': '1px solid #dee2e6',
                    'borderRadius': '5px',
                    'overflow': 'hidden'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f8f9fa'
                    },
                    {
                        'if': {'filter_query': '{Colaborador} = "Total"'},
                        'fontWeight': 'bold',
                        'backgroundColor': '#f8f9fa'
                    }
                ],
                page_size=10
            )
            
            tabelas_filiais.extend([header, tabela])
        
        # Adicionar contador de resultados
        total_filiais = len(colaboradores_filtrados.groupby(['filial', 'rede']))
        total_colaboradores = len(colaboradores_filtrados)
        
        resumo = dbc.Alert(
            [
                html.H6("📊 Resumo da consulta:", className="mb-2"),
                html.P([
                    f"Total de Filiais: {total_filiais}",
                    html.Br(),
                    f"Total de Colaboradores: {total_colaboradores}"
                ], className="mb-0")
            ],
            color="success",
            className="mb-3"
        )
        
        return html.Div([resumo] + tabelas_filiais)
        
    except Exception as e:
        print(f"Erro ao atualizar tabela de equipes: {str(e)}")
        import traceback
        traceback.print_exc()
        return html.Div(f"Erro ao gerar tabela: {str(e)}")

@app.callback(
    Output("download-excel", "data"),
    [Input("btn-export-excel", "n_clicks")],
    [State('filtro-rede-equipes', 'value'),
     State('filtro-situacao-equipes', 'value'),
     State('store-data', 'data')]
)
def export_excel(n_clicks, rede_selecionada, situacao_selecionada, data):
    """Exporta os dados filtrados para Excel"""
    if not n_clicks or not data:
        raise PreventUpdate

    try:
        # Converter dados para DataFrame
        df = pd.DataFrame(data)
        
        # Obter dados do banco de dados de redes
        network_db = NetworkDatabase()
        todos_colaboradores = network_db.get_all_employees()
        
        if todos_colaboradores.empty:
            raise PreventUpdate
        
        # Filtrar por rede se necessário
        if rede_selecionada != 'todas':
            todos_colaboradores = todos_colaboradores[todos_colaboradores['rede'] == rede_selecionada]
        
        # Criar conjunto de colaboradores com vouchers utilizados
        colaboradores_com_vouchers = set(df[
            df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)
        ]['nome_vendedor'].unique())
        
        # Filtrar colaboradores baseado na situação selecionada
        if situacao_selecionada == 'utilizado':
            colaboradores_filtrados = todos_colaboradores[
                todos_colaboradores['nome'].isin(colaboradores_com_vouchers)
            ]
        elif situacao_selecionada == 'sem_vouchers':
            colaboradores_filtrados = todos_colaboradores[
                ~todos_colaboradores['nome'].isin(colaboradores_com_vouchers)
            ]
        else:  # total
            colaboradores_filtrados = todos_colaboradores
        
        # Criar DataFrame para Excel
        excel_data = []
        for (filial, rede), grupo in colaboradores_filtrados.groupby(['filial', 'rede']):
            # Adicionar linha de cabeçalho da filial
            excel_data.append({
                'Filial/Colaborador': f'📍 {filial} - {rede}',
                'Vouchers Gerados': '',
                'Vouchers Utilizados': ''
            })
            
            # Inicializar totais da filial
            total_gerados_filial = 0
            total_utilizados_filial = 0
            
            # Adicionar colaboradores
            for _, row in grupo.iterrows():
                # Contar vouchers para este colaborador
                vouchers_gerados = len(df[df['nome_vendedor'] == row['nome']])
                vouchers_utilizados = len(df[
                    (df['nome_vendedor'] == row['nome']) & 
                    (df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False))
                ])
                
                # Acumular totais
                total_gerados_filial += vouchers_gerados
                total_utilizados_filial += vouchers_utilizados
                
                excel_data.append({
                    'Filial/Colaborador': row['nome'],
                    'Vouchers Gerados': vouchers_gerados,
                    'Vouchers Utilizados': vouchers_utilizados
                })
            
            # Adicionar linha de total da filial
            excel_data.append({
                'Filial/Colaborador': 'Total',
                'Vouchers Gerados': total_gerados_filial,
                'Vouchers Utilizados': total_utilizados_filial
            })
            
            # Adicionar linha em branco após cada filial
            excel_data.append({
                'Filial/Colaborador': '',
                'Vouchers Gerados': '',
                'Vouchers Utilizados': ''
            })
        
        # Converter para DataFrame
        df_excel = pd.DataFrame(excel_data)
        
        # Criar buffer para o arquivo Excel
        output = io.BytesIO()
        
        # Criar Excel writer
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Escrever dados
            df_excel.to_excel(writer, sheet_name='Engajamento', index=False)
            
            # Obter workbook e worksheet
            workbook = writer.book
            worksheet = writer.sheets['Engajamento']
            
            # Definir formatos
            header_format = workbook.add_format({  # type: ignore
                'bold': True,
                'bg_color': '#3498db',
                'font_color': 'white',
                'border': 1,
                'font_size': 12
            })
            
            filial_format = workbook.add_format({  # type: ignore
                'bg_color': '#f8f9fa',
                'bold': True,
                'text_wrap': True,
                'font_size': 12
            })
            
            number_format = workbook.add_format({  # type: ignore
                'num_format': '0',
                'font_size': 12
            })
            
            total_format = workbook.add_format({  # type: ignore
                'bold': True,
                'num_format': '0',
                'font_size': 12,
                'bottom': 1
            })
            
            regular_format = workbook.add_format({  # type: ignore
                'font_size': 12
            })
            
            # Aplicar formatos
            for col_num, value in enumerate(df_excel.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Ajustar largura das colunas (aumentadas em 30%)
            worksheet.set_column('A:A', 52)  # Filial/Colaborador (40 * 1.3)
            worksheet.set_column('B:C', 20)  # Vouchers (15 * 1.3)
            
            # Aplicar formatos para cada linha
            for row_num in range(1, len(df_excel) + 1):
                row_data = df_excel.iloc[row_num-1]
                
                if row_data['Filial/Colaborador'].startswith('📍'):
                    # Linha de filial
                    worksheet.set_row(row_num, None, filial_format)
                elif row_data['Filial/Colaborador'] == 'Total':
                    # Linha de total
                    worksheet.write(row_num, 0, row_data['Filial/Colaborador'], total_format)
                    worksheet.write(row_num, 1, row_data['Vouchers Gerados'], total_format)
                    worksheet.write(row_num, 2, row_data['Vouchers Utilizados'], total_format)
                elif row_data['Filial/Colaborador'] == '':
                    # Linha em branco
                    worksheet.set_row(row_num, None, regular_format)
                else:
                    # Linha de colaborador
                    worksheet.write(row_num, 0, row_data['Filial/Colaborador'], regular_format)
                    worksheet.write(row_num, 1, row_data['Vouchers Gerados'], number_format)
                    worksheet.write(row_num, 2, row_data['Vouchers Utilizados'], number_format)
        
        # Preparar arquivo para download
        output.seek(0)
        
        # Gerar nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"engajamento_equipes_{timestamp}.xlsx"
        
        return dcc.send_bytes(output.getvalue(), filename)
        
    except Exception as e:
        print(f"Erro ao exportar para Excel: {str(e)}")
        import traceback
        traceback.print_exc()
        raise PreventUpdate

# ========================
# 📥 Callbacks de Upload e Filtros
# ========================
@app.callback(
    [Output('upload-status', 'children'),
     Output('store-data', 'data'),
     Output('welcome-message', 'style'),
     Output('filters-section', 'style'),
     Output('tabs-section', 'style'),
     Output('filter-month', 'options'),
     Output('filter-network', 'options'),
     Output('filter-status', 'options')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')],
    prevent_initial_call=True
)
def handle_upload(contents, filename):
    if not contents:
        return no_update, no_update, no_update, no_update, no_update, [], [], []

    try:
        # Validar extensão do arquivo
        if not filename.lower().endswith(('.xls', '.xlsx')):
            raise ValueError("Por favor, faça upload de um arquivo Excel (.xls ou .xlsx)")

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        if df.empty:
            raise ValueError("O arquivo está vazio!")

        # Normalizar nomes das colunas
        df.columns = [unidecode(str(col)).strip().lower().replace(' ', '_').replace('ç', 'c') for col in df.columns]
        
        # Validar colunas obrigatórias
        required_columns = {
            'imei': ['imei', 'device_id', 'dispositivo'],
            'criado_em': ['criado_em', 'data_criacao', 'data', 'created_at'],
            'valor_voucher': ['valor_do_voucher', 'valor_voucher', 'voucher_value'],
            'valor_dispositivo': ['valor_do_dispositivo', 'valor_dispositivo', 'device_value'],
            'situacao_voucher': ['situacao_do_voucher', 'situacao_voucher', 'status_voucher', 'status'],
            'nome_vendedor': ['nome_do_vendedor', 'vendedor', 'seller_name'],
            'nome_filial': ['nome_da_filial', 'filial', 'branch_name'],
            'nome_rede': ['nome_da_rede', 'rede', 'network_name']
        }

        column_mapping = {}
        missing_columns = []
        for standard_name, possible_names in required_columns.items():
            found = False
            for possible_name in possible_names:
                if possible_name in df.columns:
                    column_mapping[possible_name] = standard_name
                    found = True
                    break
            if not found:
                missing_columns.append(standard_name)

        if missing_columns:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")

        # Renomear e processar colunas
        df = df.rename(columns=column_mapping)

        # Processar datas
        if 'criado_em' in df.columns:
            df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
            df = df.dropna(subset=['criado_em'])
            df['mes'] = df['criado_em'].dt.strftime('%b')
            df['mes_num'] = df['criado_em'].dt.month
            df['dia'] = df['criado_em'].dt.day
            df['ano'] = df['criado_em'].dt.year
            df['data_str'] = df['criado_em'].dt.strftime('%Y-%m-%d')

        if df.empty:
            raise ValueError("Nenhuma data válida encontrada após processamento!")

        # Limpar e converter valores numéricos
        for col in ['valor_voucher', 'valor_dispositivo']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Preparar opções para filtros
        month_options = []
        network_options = []
        status_options = []
        
        if 'mes' in df.columns and 'ano' in df.columns:
            month_options = [
                {'label': f"{month} ({year})", 'value': f"{month}_{year}"} 
                for month, year in sorted(df.groupby(['mes', 'ano']).size().index)
            ]
        
        if 'nome_rede' in df.columns:
            network_options = [
                {'label': network, 'value': network} 
                for network in sorted(df['nome_rede'].dropna().unique())
            ]
        
        if 'situacao_voucher' in df.columns:
            status_options = [
                {'label': status, 'value': status} 
                for status in sorted(df['situacao_voucher'].dropna().unique())
            ]

        success_alert = dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"✅ Arquivo '{filename}' processado com sucesso! {len(df):,} registros carregados."
        ], color="success", dismissable=True, duration=4000)

        return (
            success_alert,
            df.to_dict('records'),
            {'display': 'none'},
            {'display': 'block'},
            {'display': 'block'},
            month_options,
            network_options,
            status_options
        )

    except Exception as e:
        error_alert = dbc.Alert(f"❌ Erro ao processar arquivo: {str(e)}", 
                               color="danger", dismissable=True)
        return (
            error_alert,
            no_update,
            {'display': 'block'},
            {'display': 'none'},
            {'display': 'none'},
            [], [], []
        )

@app.callback(
    [Output('store-filtered-data', 'data'),
     Output('upload-status', 'children', allow_duplicate=True)],
    [Input('filter-month', 'value'),
     Input('filter-network', 'value'),
     Input('filter-status', 'value'),
     Input('clear-filters', 'n_clicks')],
    [State('store-data', 'data')],
    prevent_initial_call=True
)
def apply_filters(months, networks, statuses, clear_clicks, original_data):
    if not original_data:
        return no_update, no_update
    
    try:
        ctx = callback_context
        triggered = getattr(ctx, 'triggered', [])
        if triggered and 'clear-filters' in triggered[0].get('prop_id', ''):
            return original_data, dbc.Alert("Filtros limpos com sucesso!", color="info", duration=2000)
        
        df = pd.DataFrame(original_data)
        
        if months and 'mes' in df.columns and 'ano' in df.columns:
            month_year_filters = [f"{row['mes']}_{row['ano']}" for _, row in df.iterrows()]
            df = df[[mf in months for mf in month_year_filters]]
        
        if networks and 'nome_rede' in df.columns:
            df = df[df['nome_rede'].isin(networks)]
        
        if statuses and 'situacao_voucher' in df.columns:
            df = df[df['situacao_voucher'].isin(statuses)]
        
        if df.empty:
            return no_update, dbc.Alert("Nenhum dado encontrado com os filtros selecionados!", 
                                      color="warning", duration=4000)
        
        return df.to_dict('records'), no_update
    
    except Exception as e:
        return no_update, dbc.Alert(f"Erro ao aplicar filtros: {str(e)}", 
                                  color="danger", duration=4000)

# ========================
# 📊 CALLBACK PARA KPIs
# ========================
@app.callback(
    Output('kpi-section', 'children'),
    [Input('store-data', 'data'),
     Input('store-filtered-data', 'data')],
    prevent_initial_call=True
)
def update_kpis(original_data, filtered_data):
    try:
        data_to_use = filtered_data if filtered_data else original_data
        if not data_to_use:
            return html.Div()
        
        df = pd.DataFrame(data_to_use)
        return generate_kpi_cards(df)
    except Exception as e:
        return html.Div()

# ========================
# 📈 CALLBACK PARA CONTEÚDO DAS ABAS
# ========================
@app.callback(
    Output('tab-content-area', 'children'),
    [Input('main-tabs', 'value'),
     Input('store-filtered-data', 'data'),
     Input('store-data', 'data')],
    prevent_initial_call=True
)
def update_tab_content(active_tab, filtered_data, original_data):
    try:
        if active_tab == "network-base":
            return generate_network_base_content()
            
        data_to_use = filtered_data if filtered_data else original_data
        if not data_to_use:
            return dbc.Alert("Nenhum dado disponível.", color="warning")
        
        df = pd.DataFrame(data_to_use)
        original_df = pd.DataFrame(original_data) if original_data else df
        
        if active_tab == "overview":
            return generate_overview_content(df)
        elif active_tab == "networks":
            return generate_networks_content(df)
        elif active_tab == "rankings":
            return generate_rankings_content(df)
        elif active_tab == "projections":
            return generate_projections_content(original_df, df)
        elif active_tab == "engagement":
            return generate_engagement_content(df, network_db)
        else:
            return html.Div("Aba não encontrada")
    except Exception as e:
        return dbc.Alert(f"Erro: {str(e)}", color="danger")

# ========================
# JavaScript para exportação PDF
# ========================
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            // Adicionar script para capturar o dashboard e exportar como PDF
            html2canvas(document.querySelector(".container-fluid")).then(canvas => {
                const imgData = canvas.toDataURL('image/png');
                const pdf = new jsPDF('p', 'mm', 'a4');
                const imgProps = pdf.getImageProperties(imgData);
                const pdfWidth = pdf.internal.pageSize.getWidth();
                const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
                pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
                pdf.save('dashboard-renov.pdf');
            });
        }
        return '';
    }
    """,
    Output("export-pdf", "n_clicks"),
    Input("export-pdf", "n_clicks"),
    prevent_initial_call=True
)

# ========================
# 🔄 Callback Principal de Roteamento
# ========================
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
    
    triggered = getattr(ctx, 'triggered', [])
    if not triggered:
        return create_login_layout()
    
    trigger_id = triggered[0].get('prop_id', '').split('.')[0]
    
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

# ========================
# 🔄 Callbacks de Navegação
# ========================
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    [Input('show-login', 'n_clicks')],
    prevent_initial_call=True
)
def handle_navigation(show_login_clicks):
    if not show_login_clicks:
        raise PreventUpdate
    return '/'

# ========================
# 🔐 Callbacks de Autenticação
# ========================
@app.callback(
    [Output('url', 'pathname', allow_duplicate=True),
     Output('auth-status', 'children', allow_duplicate=True)],
    [Input('login-button', 'n_clicks')],
    [State('login-username', 'value'),
     State('login-password', 'value')],
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password):
    if not n_clicks:
        raise PreventUpdate
    
    if not username or not password:
        return no_update, dbc.Alert(
            "Por favor, preencha todos os campos.",
            color="warning",
            duration=4000
        )
    
    user = db.verify_user(username, password)
    
    if user:
        return '/dashboard', dbc.Alert(
            "Login realizado com sucesso!",
            color="success",
            duration=2000
        )
    
    return no_update, dbc.Alert(
        "Usuário ou senha inválidos.",
        color="danger",
        duration=4000
    )

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    [Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return '/'

# ========================
# 📥 Callbacks de Upload de Redes e Colaboradores
# ========================
@app.callback(
    Output('network-upload-status', 'children'),
    [Input('upload-networks-branches-file', 'contents'),
     Input('upload-employees-file', 'contents')],
    [State('upload-networks-branches-file', 'filename'),
     State('upload-employees-file', 'filename')],
    prevent_initial_call=True
)
def handle_network_upload(networks_contents, employees_contents, networks_filename, employees_filename):
    ctx = callback_context
    if not ctx.triggered:
        return no_update

    try:
        triggered = getattr(ctx, 'triggered', [])
        if not triggered:
            return no_update
            
        trigger_id = triggered[0].get('prop_id', '').split('.')[0]
        db = NetworkDatabase()
        
        if trigger_id == 'upload-networks-branches-file' and networks_contents:
            print("\n=== Processando upload de Redes e Filiais ===")
            content_type, content_string = networks_contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.read_excel(io.BytesIO(decoded))
            
            print(f"Dados lidos do arquivo:")
            print(df.head())
            print(f"Total de registros: {len(df)}")
            
            success, message = db.update_networks_and_branches(df)
            
            if success:
                db.debug_data()
                return dbc.Alert(
                    f"✅ Base de redes e filiais atualizada! Arquivo: {networks_filename}",
                    color="success",
                    dismissable=True,
                    duration=4000
                )
            else:
                return dbc.Alert(
                    f"❌ Erro ao atualizar base de redes e filiais: {message}",
                    color="danger",
                    dismissable=True
                )
                
        elif trigger_id == 'upload-employees-file' and employees_contents:
            print("\n=== Processando upload de Colaboradores ===")
            try:
                content_type, content_string = employees_contents.split(',')
                decoded = base64.b64decode(content_string)
                df = pd.read_excel(io.BytesIO(decoded))
                
                print("Colunas encontradas no arquivo:")
                print(df.columns.tolist())
                
                # Normalizar nomes das colunas
                df.columns = [unidecode(str(col)).strip().lower().replace(' ', '_') for col in df.columns]
                print("\nColunas após normalização:")
                print(df.columns.tolist())
                
                # Mapear colunas esperadas
                expected_columns = {
                    'colaborador': ['colaborador', 'nome', 'nome_colaborador', 'funcionario'],
                    'filial': ['filial', 'nome_filial', 'loja'],
                    'rede': ['rede', 'nome_rede', 'network'],
                    'ativo': ['ativo', 'status', 'situacao'],
                    'data_cadastro': ['data_cadastro', 'data_registro', 'cadastro']
                }
                
                # Verificar e mapear colunas
                column_mapping = {}
                missing_columns = []
                
                for target_col, possible_names in expected_columns.items():
                    found = False
                    for possible_name in possible_names:
                        if possible_name in df.columns:
                            column_mapping[possible_name] = target_col
                            found = True
                            break
                    if not found:
                        missing_columns.append(target_col)
                
                if missing_columns:
                    error_msg = f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}"
                    print(f"Erro: {error_msg}")
                    return dbc.Alert(
                        f"❌ {error_msg}",
                        color="danger",
                        dismissable=True
                    )
                
                # Renomear colunas
                df = df.rename(columns=column_mapping)
                
                print("\nPrimeiras linhas após mapeamento:")
                print(df.head())
                print(f"Total de registros: {len(df)}")
                
                # Processar dados antes de enviar para o banco
                if 'data_cadastro' in df.columns:
                    df['data_cadastro'] = pd.to_datetime(df['data_cadastro'], errors='coerce')
                    df['data_cadastro'] = df['data_cadastro'].dt.strftime('%Y-%m-%d')
                
                if 'ativo' in df.columns:
                    df['ativo'] = df['ativo'].astype(str).str.upper()
                
                # Remover linhas com valores nulos em colunas críticas
                df = df.dropna(subset=['colaborador', 'filial', 'rede'])
                
                print("\nDados processados:")
                print(f"Registros após limpeza: {len(df)}")
                
                success, message = db.update_employees(df)
                
                if success:
                    db.debug_data()
                    return dbc.Alert(
                        f"✅ Base de colaboradores atualizada! Arquivo: {employees_filename}",
                        color="success",
                        dismissable=True,
                        duration=4000
                    )
                else:
                    print(f"Erro ao atualizar base: {message}")
                    return dbc.Alert(
                        f"❌ Erro ao atualizar base de colaboradores: {message}",
                        color="danger",
                        dismissable=True
                    )
            except Exception as e:
                print(f"Erro ao processar arquivo de colaboradores: {str(e)}")
                import traceback
                traceback.print_exc()
                return dbc.Alert(
                    f"❌ Erro ao processar arquivo de colaboradores: {str(e)}",
                    color="danger",
                    dismissable=True
                )
    
    except Exception as e:
        print(f"Erro durante o upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(
            f"❌ Erro ao processar arquivo: {str(e)}",
            color="danger",
            dismissable=True
        )

    return no_update

@app.callback(
    Output('tab-content-area', 'children', allow_duplicate=True),
    [Input('network-upload-status', 'children'),
     Input('main-tabs', 'value')],
    prevent_initial_call=True
)
def update_network_base_tab(upload_status, current_tab):
    """Atualiza a aba de base de redes quando há um novo upload"""
    print("\n=== Atualizando conteúdo da aba de base ===")
    print(f"Tab atual: {current_tab}")
    print(f"Status do upload: {upload_status}")
    
    if not upload_status or current_tab != 'network-base':
        return no_update
    
    try:
        db = NetworkDatabase()
        stats = db.get_network_stats()
        print("\nEstatísticas atuais:")
        print(f"Redes: {stats['total_networks']}")
        print(f"Filiais: {stats['total_branches']}")
        print(f"Colaboradores: {stats['total_employees']}")
        
        return generate_network_base_content()
    except Exception as e:
        print(f"Erro ao atualizar aba: {str(e)}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(
            f"Erro ao atualizar conteúdo: {str(e)}",
            color="danger"
        )

# ========================
# 🔚 Execução e Documentação
# ========================

"""
Instruções de Execução:

1. Desenvolvimento Local:
   python app.py
   - O servidor iniciará em http://0.0.0.0:8080
   - Variáveis de ambiente opcionais:
     * FLASK_ENV=development (para modo debug)
     * PORT=8080 (ou outra porta desejada)

2. Produção:
   gunicorn wsgi:server
   - O servidor iniciará em http://0.0.0.0:8080 (ou a porta definida em $PORT)
   - Variáveis de ambiente necessárias:
     * FLASK_ENV=production
     * PORT=8080 (ou porta desejada)
     * SECRET_KEY=chave_secreta_segura

3. Usando Procfile:
   web: gunicorn wsgi:server --workers 4 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT
   - Usa automaticamente a variável $PORT do ambiente
   - Configurado para performance em produção
   - Recomendado para deploy no GitHub ou serviços similares
"""

if __name__ == '__main__':
    try:
        # Configuração inicial
        is_dev = os.environ.get('FLASK_ENV') == 'development'
        
        # Mensagens de inicialização
        print("="*50)
        print(f"Iniciando servidor em http://{HOST}:{PORT}")
        print(f"Ambiente: {'development' if is_dev else 'production'}")
        print(f"Porta: {PORT}")
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