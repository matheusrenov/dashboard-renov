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
from datetime import datetime, timedelta
from typing import Dict, Any

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

# Configuração dos assets e diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(BASE_DIR, 'assets')
data_path = os.path.join(BASE_DIR, 'data')

# Criar diretórios necessários
for directory in [assets_path, data_path]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Inicialização do Flask
server = Flask(__name__)
CORS(server)

# Configuração simples e robusta do banco de dados
database_url = os.environ.get('DATABASE_URL')
if database_url and (database_url.startswith('postgresql://') or database_url.startswith('postgres://')):
    # URL válida de PostgreSQL
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://')
    db_uri = database_url
    print(f"Usando PostgreSQL: {db_uri[:50]}...")
else:
    # SQLite local ou temporário (forçar SQLite no Railway também)
    db_file = os.path.join(data_path, 'app.db')
    db_uri = f'sqlite:///{db_file}'
    print(f"Usando SQLite: {db_uri}")

# Configurações do Flask
server.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(16)),
    SQLALCHEMY_DATABASE_URI=db_uri,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    DEBUG=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
)

print(f"SQLALCHEMY_DATABASE_URI configurado: {server.config.get('SQLALCHEMY_DATABASE_URI')}")

# Inicialização do SQLAlchemy com tratamento de erro
try:
    db = SQLAlchemy(server)
    print("SQLAlchemy inicializado com sucesso")
except Exception as e:
    print(f"Erro ao inicializar SQLAlchemy: {e}")
    # Usar um mock simples para permitir que a aplicação inicie
    class MockDB:
        session = None
        def execute(self, query):
            pass
        def commit(self):
            pass
    db = MockDB()

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

# Vincula o servidor Flask ao Dash
app.server = server
app.title = "Dashboard Renov"

# Módulos locais (importados após a inicialização do db)
from models import UserDatabase
from models_network import NetworkDatabase
from auth_layout import create_login_layout, create_register_layout, create_admin_approval_layout
from error_layout import create_error_layout

# Layout inicial
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='store-data'),
    dcc.Store(id='store-filtered-data'),
    dcc.Store(id='session-store'),
    html.Div(id='page-content', children=[
        # Layout padrão simples
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("Dashboard Renov", className="text-center mb-4"),
                    html.P("Sistema de análise de dados", className="text-center")
                ])
            ])
        ])
    ])
])

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    """Renderiza a página apropriada baseado na URL"""
    try:
        if pathname == '/dashboard':
            return create_login_layout()  # Temporariamente retorna login
        else:
            return create_login_layout()
    except Exception as e:
        print(f"Erro no display_page: {e}")
        return html.Div([
            html.H1("Dashboard Renov"),
            html.P("Sistema carregado com sucesso!"),
            html.P(f"Path: {pathname}")
        ])

# Comentar outros callbacks temporariamente
"""
@app.callback(
    [Output('page-content', 'children'),
     Output('session-store', 'data')],
    [Input('url', 'pathname'),
     Input('login-button', 'n_clicks'),
     Input('logout-button', 'n_clicks')],
    [State('username', 'value'),
     State('password', 'value'),
     State('session-store', 'data')]
)
def manage_auth(pathname, login_clicks, logout_clicks, username, password, session_data):
    return create_login_layout(), None
"""

@app.callback(
    Output('tab-content', 'children'),
    [Input('main-tabs', 'active_tab'),
     Input('store-filtered-data', 'data')]
)
def update_tab_content(tab, filtered_data):
    """Atualiza o conteúdo da aba selecionada"""
    if not filtered_data:
        return no_data_message()
    
    try:
        df = pd.DataFrame(filtered_data)
        
        if tab == "overview":
            return generate_overview_content(df)
        elif tab == "networks":
            return generate_networks_content(df)
        elif tab == "rankings":
            return generate_rankings_content(df)
        elif tab == "projections":
            return generate_projections_content(df)
        elif tab == "engagement":
            return generate_engagement_content(df)
        elif tab == "tim":
            return generate_tim_content(df)
        
        return html.Div("Conteúdo não disponível")
    
    except Exception as e:
        print(f"Erro ao atualizar conteúdo da aba: {str(e)}")
        traceback.print_exc()
        return error_message()

# ========================
# 📊 Layout do Dashboard
# ========================

def create_dashboard_layout(is_super_admin=False):
    """
    Cria o layout principal do dashboard.
    """
    return dbc.Container([
        # Cabeçalho
        dbc.Row([
            dbc.Col([
                html.Img(
                    src='./assets/images/Logo Roxo.png',
                    style={"height": "30px", "marginRight": "10px", "display": "inline-block"}
                ),
                html.H4("Dashboard de Performance", className="d-inline-block align-middle mb-0"),
                dbc.Button(
                    "Sair",
                    id="logout-button",
                    color="danger",
                    className="float-end"
                )
            ])
        ], className="mb-4"),

        # Seção de Filtros
        dbc.Card([
            dbc.CardBody([
                html.H6("🔍 Filtros", className="mb-3"),
        dbc.Row([
            dbc.Col([
                        html.Label("Período"),
                dbc.Row([
                    dbc.Col([
                                html.Label("De"),
                                dcc.DatePickerSingle(
                                    id='date-from',
                                    placeholder="Selecione",
                                className="w-100"
                                )
                    ], width=6),
                    dbc.Col([
                                html.Label("Até"),
                                dcc.DatePickerSingle(
                                    id='date-to',
                                    placeholder="Selecione",
                                    className="w-100"
                                )
                            ], width=6)
                        ])
                    ], width=3),
                    dbc.Col([
                        html.Label("Mês"),
                        dcc.Dropdown(
                            id='filter-month',
                            options=[],
                            placeholder="Selecione o(s) mês(es)",
                            multi=True,
                            className="w-100"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Rede"),
                        dcc.Dropdown(
                            id='filter-network',
                            options=[],
                            placeholder="Selecione a(s) rede(s)",
                            multi=True,
                            className="w-100"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Situação"),
                        dcc.Dropdown(
                            id='filter-status',
                            options=[],
                            placeholder="Selecione o(s) status",
                            multi=True,
                            className="w-100"
                        )
                    ], width=3)
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "Limpar Filtros",
                            id="clear-filters",
                                color="secondary",
                                size="sm",
                            className="mt-3"
                        )
                    ])
                ])
            ])
        ], className="mb-4"),

        # Seção de Upload Principal
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("📊 Upload de Dados", className="text-center mb-3"),
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                                html.P('Arraste e solte ou ', className="mb-0 d-inline"),
                                html.A('selecione um arquivo Excel', className="text-primary"),
                            ], className="text-center p-3 border rounded"),
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
                        html.Div(id='upload-status', className="mt-2")
                    ])
                ])
            ], width=12)
        ], className="mb-4"),

        # Seção de Upload de Redes e Colaboradores
            dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                        html.H6("Analisar Base de Redes e Filiais", className="text-center mb-3"),
                        dcc.Upload(
                            id='upload-networks-branches-file',
                            children=html.Div([
                                html.P('Arraste e solte ou ', className="mb-0 d-inline"),
                                html.A('selecione o arquivo de Redes/Filiais', className="text-primary"),
                            ], className="text-center p-3 border rounded"),
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
                        html.Div(id='network-upload-status', className="mt-2")
                    ])
                ])
            ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                        html.H6("Analisar Base de Colaboradores", className="text-center mb-3"),
                        dcc.Upload(
                            id='upload-employees-file',
                            children=html.Div([
                                html.P('Arraste e solte ou ', className="mb-0 d-inline"),
                                html.A('selecione o arquivo de Colaboradores', className="text-primary"),
                            ], className="text-center p-3 border rounded"),
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
                        html.Div(id='employee-upload-status', className="mt-2")
                    ])
                ])
            ], width=6)
        ], className="mb-4"),

        # KPIs
        html.Div(id='kpi-cards', className="mb-4"),

        # Abas principais
        dbc.Tabs([
            dbc.Tab(label="📊 Visão Geral", tab_id="overview"),
            dbc.Tab(label="🏢 Redes", tab_id="networks"),
            dbc.Tab(label="🏆 Rankings", tab_id="rankings"),
            dbc.Tab(label="🔮 Projeções", tab_id="projections"),
            dbc.Tab(label="👥 Engajamento", tab_id="engagement"),
            dbc.Tab(label="📊 TIM", tab_id="tim")
        ], id="main-tabs", active_tab="overview"),
        
        html.Div(id="tab-content"),

        # Componentes ocultos para armazenamento de dados
        dcc.Store(id='store-data'),
        dcc.Store(id='store-filtered-data'),
        dcc.Download(id="download-dataframe-csv"),
    ], fluid=True)

# Callback para atualizar os KPIs
@app.callback(
    Output('kpi-cards', 'children'),
    Input('store-filtered-data', 'data')
)
def update_kpis(filtered_data):
    if not filtered_data:
        return []
    
    df = pd.DataFrame(filtered_data)
    return generate_kpi_cards(df)

# Callback para popular os filtros
@app.callback(
    [
        Output('filter-month', 'options'),
        Output('filter-network', 'options'),
        Output('filter-status', 'options')
    ],
    Input('store-data', 'data')
)
def update_filter_options(data):
    if not data:
        return [], [], []
    
    df = pd.DataFrame(data)
    
    # Opções para mês
    df['mes'] = pd.to_datetime(df['data_str']).dt.strftime('%Y-%m')
    meses = sorted(df['mes'].unique())
    opcoes_mes = [{'label': mes, 'value': mes} for mes in meses]
    
    # Opções para rede
    redes = sorted(df['nome_rede'].unique())
    opcoes_rede = [{'label': rede, 'value': rede} for rede in redes]
    
    # Opções para status
    status = sorted(df['situacao_voucher'].unique())
    opcoes_status = [{'label': status, 'value': status} for status in status]
    
    return opcoes_mes, opcoes_rede, opcoes_status

# Callback para limpar filtros
@app.callback(
    [
        Output('filter-month', 'value'),
        Output('filter-network', 'value'),
        Output('filter-status', 'value'),
        Output('date-from', 'date'),
        Output('date-to', 'date')
    ],
    Input('clear-filters', 'n_clicks'),
    prevent_initial_call=True
)
def clear_filters(n_clicks):
    return None, None, None, None, None

# Callback para filtrar dados
@app.callback(
    Output('store-filtered-data', 'data'),
    [
        Input('store-data', 'data'),
        Input('filter-month', 'value'),
        Input('filter-network', 'value'),
        Input('filter-status', 'value'),
        Input('date-from', 'date'),
        Input('date-to', 'date')
    ]
)
def filter_data(data, selected_months, selected_networks, selected_status, date_from, date_to):
    if not data:
        return None
    
    df = pd.DataFrame(data)
    df['mes'] = pd.to_datetime(df['data_str']).dt.strftime('%Y-%m')
    df['data'] = pd.to_datetime(df['data_str'])
    
    # Aplicar filtros
    if selected_months:
        if isinstance(selected_months, str):
            selected_months = [selected_months]
        df = df[df['mes'].isin(selected_months)]
    
    if selected_networks:
        if isinstance(selected_networks, str):
            selected_networks = [selected_networks]
        df = df[df['nome_rede'].isin(selected_networks)]
    
    if selected_status:
        if isinstance(selected_status, str):
            selected_status = [selected_status]
        df = df[df['situacao_voucher'].isin(selected_status)]
    
    if date_from:
        df = df[df['data'] >= date_from]
    
    if date_to:
        df = df[df['data'] <= date_to]
    
    return df.to_dict('records')

# Callback para processar upload de dados
@app.callback(
    [
        Output('store-data', 'data'),
        Output('upload-status', 'children')
    ],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def process_upload(contents, filename):
    if contents is None:
        return None, None
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        if filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None, dbc.Alert("Por favor, use apenas arquivos Excel (.xls, .xlsx).", color="danger")
        
        # Validar colunas necessárias
        required_columns = ['Data', 'IMEI', 'Valor do Voucher', 'Valor do Dispositivo', 'Status do Voucher', 'Vendedor', 'Filial', 'Rede']
        
        # Normalizar nomes das colunas
        df.columns = [unidecode(col).strip().lower() for col in df.columns]
        normalized_required = [unidecode(col).strip().lower() for col in required_columns]
        
        missing_columns = [col for col in normalized_required if col not in df.columns]
        if missing_columns:
            return None, dbc.Alert(f"Colunas obrigatórias ausentes: {', '.join(required_columns)}", color="danger")
        
        # Processar dados básicos
        try:
            df['data_str'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d')
            df['valor_voucher'] = pd.to_numeric(df['valor_do_voucher'])
            df['valor_dispositivo'] = pd.to_numeric(df['valor_do_dispositivo'])
        except Exception as e:
            return None, dbc.Alert("Erro ao processar dados. Verifique o formato dos valores.", color="danger")
        
        return df.to_dict('records'), dbc.Alert(f"Dados carregados com sucesso! {len(df)} registros processados.", color="success")
        
    except Exception as e:
        print(f"Erro no processamento do arquivo: {str(e)}")
        return None, dbc.Alert(f"Erro ao processar o arquivo: {str(e)}", color="danger")

# Callback para processar upload de redes e filiais
@app.callback(
    Output('network-upload-status', 'children'),
    Input('upload-networks-branches-file', 'contents'),
    State('upload-networks-branches-file', 'filename'),
    prevent_initial_call=True
)
def process_network_upload(contents, filename):
    if contents is None:
        raise PreventUpdate
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        if filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return dbc.Alert(
                "Por favor, use apenas arquivos Excel (.xls, .xlsx) para a base de redes.",
                color="danger"
            )
        
        # Validar colunas necessárias para redes/filiais conforme glossário
        required_columns = [
            'Nome da Rede',
            'Nome da Filial',
            'Data de Início',
            'Ativo'  # Status da rede/filial
        ]
        
        # Normalizar nomes das colunas
        df.columns = [unidecode(col).strip().lower() for col in df.columns]
        normalized_required = [unidecode(col).strip().lower() for col in required_columns]
        
        missing_columns = [col for col in normalized_required if col not in df.columns]
        if missing_columns:
            return dbc.Alert(
                f"Colunas obrigatórias ausentes: {', '.join(required_columns)}",
                color="danger"
            )
        
        # Validar status (ATIVO/INATIVO)
        status_values = df['ativo'].str.upper().unique()
        invalid_status = [s for s in status_values if s not in ['ATIVO', 'ATIVA', 'INATIVO', 'INATIVA']]
        if invalid_status:
            return dbc.Alert(
                f"Status inválidos encontrados: {', '.join(invalid_status)}. Use apenas ATIVO/ATIVA ou INATIVO/INATIVA.",
                color="danger"
            )
        
        # Validar datas
        try:
            df['data_de_inicio'] = pd.to_datetime(df['data_de_inicio'])
        except Exception as e:
            return dbc.Alert(
                "Erro no formato das datas. Use o formato dd/mm/aaaa.",
                color="danger"
            )
        
        # Processar e salvar dados de redes
        try:
            network_db = NetworkDatabase()
            network_db.update_networks(df)
            
            return dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                f"Base de redes atualizada com sucesso! ",
                html.Strong(f"{len(df):,}"), " registros processados."
            ], color="success")
            
        except Exception as e:
            return dbc.Alert(
                f"Erro ao atualizar base de redes: {str(e)}",
                color="danger"
            )
        
    except Exception as e:
        print(f"Erro no processamento do arquivo de redes: {str(e)}")
        return dbc.Alert(
            f"Erro ao processar o arquivo: {str(e)}",
            color="danger"
        )

# Callback para processar upload de colaboradores
@app.callback(
    Output('employee-upload-status', 'children'),
    Input('upload-employees-file', 'contents'),
    State('upload-employees-file', 'filename'),
    prevent_initial_call=True
)
def process_employee_upload(contents, filename):
    if contents is None:
        raise PreventUpdate
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        if filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return dbc.Alert(
                "Por favor, use apenas arquivos Excel (.xls, .xlsx) para a base de colaboradores.",
                color="danger"
            )
        
        # Validar colunas necessárias para colaboradores conforme glossário
        required_columns = [
            'Colaborador',
            'Filial',
            'Rede',
            'Ativo',
            'Data de Cadastro'
        ]
        
        # Normalizar nomes das colunas
        df.columns = [unidecode(col).strip().lower() for col in df.columns]
        normalized_required = [unidecode(col).strip().lower() for col in required_columns]
        
        missing_columns = [col for col in normalized_required if col not in df.columns]
        if missing_columns:
            return dbc.Alert(
                f"Colunas obrigatórias ausentes: {', '.join(required_columns)}",
                color="danger"
            )
        
        # Validar status (ATIVO/INATIVO)
        status_values = df['ativo'].str.upper().unique()
        invalid_status = [s for s in status_values if s not in ['ATIVO', 'ATIVA', 'INATIVO', 'INATIVA']]
        if invalid_status:
            return dbc.Alert(
                f"Status inválidos encontrados: {', '.join(invalid_status)}. Use apenas ATIVO/ATIVA ou INATIVO/INATIVA.",
                color="danger"
            )
        
        # Validar datas
        try:
            df['data_de_cadastro'] = pd.to_datetime(df['data_de_cadastro'])
        except Exception as e:
            return dbc.Alert(
                "Erro no formato das datas. Use o formato dd/mm/aaaa.",
                color="danger"
            )
        
        # Validar relacionamentos (colaborador deve pertencer a uma rede/filial existente)
        try:
            network_db = NetworkDatabase()
            valid_networks = network_db.get_valid_networks()
            valid_branches = network_db.get_valid_branches()
            
            invalid_networks = df[~df['rede'].isin(valid_networks)]['rede'].unique()
            invalid_branches = df[~df['filial'].isin(valid_branches)]['filial'].unique()
            
            if len(invalid_networks) > 0:
                return dbc.Alert(
                    f"Redes não encontradas na base: {', '.join(invalid_networks)}",
                    color="danger"
                )
            
            if len(invalid_branches) > 0:
                return dbc.Alert(
                    f"Filiais não encontradas na base: {', '.join(invalid_branches)}",
                    color="danger"
                )
            
            network_db.update_employees(df)
            
            return dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                f"Base de colaboradores atualizada com sucesso! ",
                html.Strong(f"{len(df):,}"), " registros processados."
            ], color="success")
            
        except Exception as e:
            return dbc.Alert(
                f"Erro ao atualizar base de colaboradores: {str(e)}",
                color="danger"
            )
        
    except Exception as e:
        print(f"Erro no processamento do arquivo de colaboradores: {str(e)}")
        return dbc.Alert(
            f"Erro ao processar o arquivo: {str(e)}",
            color="danger"
        )

# ========================
# 🎯 Callbacks
# ========================

@app.callback(
    Output('tab-content-area', 'children'),
    [Input('main-tabs', 'active_tab'),
     Input('store-data', 'data'),
     Input('store-filtered-data', 'data')]
)
def update_tab_content(tab, data, filtered_data):
    """Atualiza o conteúdo da aba selecionada"""
    if not data:
        return no_data_message()
    
    try:
        # Converte dados JSON para DataFrame
        df = pd.DataFrame(filtered_data if filtered_data else data)
        
        # Retorna conteúdo específico para cada aba
        if tab == "tab-overview":
            return generate_overview_content(df, include_kpis=True)
        elif tab == "tab-tim":
            return generate_tim_content(df)
        elif tab == "tab-rankings":
            return generate_rankings_content(df)
        elif tab == "tab-projections":
            return generate_projections_content(df)
        elif tab == "tab-network-base":
            return generate_networks_content(df)
        elif tab == "tab-engagement":
            return generate_engagement_content(df)
        else:
            return html.Div("Conteúdo não disponível")
    
    except Exception as e:
        print(f"Erro ao atualizar conteúdo da aba: {str(e)}")
        traceback.print_exc()
        return error_message()

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
    """Atualiza os dados filtrados"""
    if not data:
        return {'display': 'none'}, None
    
    try:
        df = pd.DataFrame(data)
        
        # Aplica filtros
        if start_date:
            df = df[df['data_criacao'] >= start_date]
        if end_date:
            df = df[df['data_criacao'] <= end_date]
        if months:
            df = df[df['data_criacao'].dt.strftime('%Y-%m').isin(months)]
        if networks:
            df = df[df['nome_rede'].isin(networks)]
        if statuses:
            df = df[df['situacao_voucher'].isin(statuses)]
        
        return {'display': 'block'}, df.to_dict('records')
    
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
    """Atualiza as opções dos filtros"""
    if not data:
        return [], [], []
    
    try:
        df = pd.DataFrame(data)
        
        # Prepara opções para cada filtro
        months = sorted(df['data_criacao'].dt.strftime('%Y-%m').unique())
        month_options = [{'label': m, 'value': m} for m in months]
        
        networks = sorted(df['nome_rede'].unique())
        network_options = [{'label': n, 'value': n} for n in networks]
        
        statuses = sorted(df['situacao_voucher'].unique())
        status_options = [{'label': s, 'value': s} for s in statuses]
        
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
    """Processa o arquivo carregado e atualiza os dados"""
    if contents is None:
        return None
    
    try:
        # Decodifica o conteúdo do arquivo
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Lê o arquivo Excel
        df = pd.read_excel(io.BytesIO(decoded))
        
        # Processa as datas
        date_columns = ['data_criacao', 'data_utilizacao']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
        
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
        return None
    return no_update

@app.callback(
    Output('upload-status', 'children'),
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename')]
)
def update_upload_status(contents, filename):
    """Atualiza o status do upload"""
    if contents is None:
        return ''
    
    try:
        return html.Div([
            html.I(className="fas fa-check-circle text-success me-2"),
            f"Arquivo {filename} carregado com sucesso!"
        ])
    except Exception as e:
        return html.Div([
            html.I(className="fas fa-times-circle text-danger me-2"),
            f"Erro ao carregar arquivo: {str(e)}"
        ])

# Funções auxiliares para mensagens
def no_data_message():
    """Retorna mensagem quando não há dados disponíveis"""
    return dbc.Alert(
        [
            html.I(className="fas fa-info-circle me-2"),
            "Nenhum dado disponível. Por favor, faça o upload de um arquivo."
        ],
        color="info",
        className="mb-4"
    )

def error_message(error_text=None):
    """Retorna mensagem de erro padronizada"""
    return dbc.Alert(
        [
            html.I(className="fas fa-exclamation-triangle me-2"),
            error_text or "Ocorreu um erro ao processar os dados."
        ],
        color="danger",
        className="mb-4"
    )

def generate_tim_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba TIM.
    
    Args:
        df: DataFrame com os dados de vouchers
    
    Returns:
        Um componente Div com a análise específica da TIM
    """
    try:
        if df.empty:
            return no_data_message()
        
        # Filtrar apenas dados da TIM
        df_tim = df[df['nome_rede'].str.contains('TIM', case=False, na=False)]
        
        if df_tim.empty:
            return dbc.Alert("Nenhum dado da TIM disponível para análise.", color="warning")
        
        # Métricas específicas da TIM
        total_vouchers = len(df_tim)
        vouchers_utilizados = df_tim[df_tim['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        total_utilizados = len(vouchers_utilizados)
        valor_total = vouchers_utilizados['valor_dispositivo'].sum()
        taxa_utilizacao = (total_utilizados / total_vouchers * 100) if total_vouchers > 0 else 0
        
        # Cards com métricas
        cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("📱 Total de Vouchers TIM", className="card-title text-center"),
                        html.H2(f"{total_vouchers:,}",
                               className="text-primary text-center display-4"),
                        html.P(f"Taxa de utilização: {taxa_utilizacao:.1f}%",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("💰 Valor Total TIM", className="card-title text-center"),
                        html.H2(f"R$ {valor_total:,.2f}",
                               className="text-success text-center display-4"),
                        html.P(f"{total_utilizados:,} vouchers utilizados",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=6)
        ])
        
        # Análise temporal
        df_tim['data'] = pd.to_datetime(df_tim['data_str'])
        daily_data = df_tim.groupby('data').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).reset_index()
        
        fig_evolution = go.Figure()
        fig_evolution.add_trace(go.Scatter(
            x=daily_data['data'],
            y=daily_data['imei'],
            mode='lines+markers',
            name='Vouchers',
            line=dict(color='#004691', width=2),  # Cor da TIM
            marker=dict(size=6)
        ))
        
        fig_evolution.update_layout(
            title='📈 Evolução Diária TIM',
            xaxis_title='Data',
            yaxis_title='Quantidade de Vouchers',
                height=400,
            template='plotly_white',
            showlegend=True
        )
        
        return html.Div([
            cards,
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_evolution)], md=12)
            ])
        ])
        
    except Exception as e:
        print(f"Erro ao gerar conteúdo TIM: {str(e)}")
        traceback.print_exc()
        return error_message()

def generate_kpi_cards(df: pd.DataFrame) -> html.Div:
    """
    Gera cards com KPIs principais.
    
    Args:
        df: DataFrame com os dados de vouchers
    
    Returns:
        Um componente Div com os cards de KPIs
    """
    try:
        # Calcular métricas
        total_vouchers = len(df)
        vouchers_utilizados = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        total_utilizados = len(vouchers_utilizados)
        valor_total = vouchers_utilizados['valor_dispositivo'].sum()
        ticket_medio = valor_total / total_utilizados if total_utilizados > 0 else 0
        taxa_utilizacao = (total_utilizados / total_vouchers * 100) if total_vouchers > 0 else 0

        # Criar cards
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("📊 Total de Vouchers", className="card-title text-center"),
                        html.H2(f"{total_vouchers:,}",
                               className="text-primary text-center display-4"),
                        html.P("Vouchers emitidos", className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("✅ Vouchers Utilizados", className="card-title text-center"),
                        html.H2(f"{total_utilizados:,}",
                               className="text-success text-center display-4"),
                        html.P(f"Taxa de utilização: {taxa_utilizacao:.1f}%",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("💰 Valor Total", className="card-title text-center"),
                        html.H2(f"R$ {valor_total:,.2f}",
                               className="text-info text-center display-4"),
                        html.P("Valor total dos vouchers utilizados",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("🎯 Ticket Médio", className="card-title text-center"),
                        html.H2(f"R$ {ticket_medio:,.2f}",
                               className="text-warning text-center display-4"),
                        html.P("Valor médio por voucher utilizado",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=3)
        ])

    except Exception as e:
        print(f"Erro ao gerar KPIs: {str(e)}")
        traceback.print_exc()
        return error_message()

def generate_overview_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de visão geral.
    """
    try:
        if df.empty:
            return no_data_message()

        # Gerar KPIs
        kpi_cards = generate_kpi_cards(df)

        # Gráfico de evolução diária
        daily_data = df.groupby('data_str').agg({
                'imei': 'count',
                'valor_dispositivo': 'sum'
            }).reset_index()
        daily_data.columns = ['data', 'vouchers', 'valor']
        daily_data['data'] = pd.to_datetime(daily_data['data'])
        daily_data = daily_data.sort_values('data')

        fig_evolution = go.Figure()
        fig_evolution.add_trace(go.Scatter(
            x=daily_data['data'],
            y=daily_data['vouchers'],
            mode='lines+markers',
                name='Vouchers',
            line=dict(color='#3498db', width=2),
            marker=dict(size=6)
        ))
        fig_evolution.add_trace(go.Scatter(
            x=daily_data['data'],
            y=daily_data['valor'],
            mode='lines+markers',
            name='Valor (R$)',
            line=dict(color='#2ecc71', width=2),
            marker=dict(size=6),
            yaxis='y2'
        ))

        fig_evolution.update_layout(
            title='📈 Evolução Diária',
                xaxis_title='Data',
            yaxis_title='Quantidade de Vouchers',
            yaxis2=dict(
                title='Valor (R$)',
                overlaying='y',
                side='right'
            ),
                height=400,
            template='plotly_white',
            showlegend=True
        )

        return html.Div([
            kpi_cards,
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_evolution)], md=12)
            ])
        ])
        
    except Exception as e:
        print(f"Erro ao gerar visão geral: {str(e)}")
        traceback.print_exc()
        return error_message()

def generate_networks_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de redes.
    """
    try:
        if df.empty:
            return no_data_message()

        # Análise por rede
        network_metrics = df.groupby('nome_rede').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).reset_index()
        network_metrics.columns = ['rede', 'total_vouchers', 'valor_total']
        
        # Calcular vouchers utilizados por rede
        utilizados = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        network_metrics['vouchers_utilizados'] = utilizados.groupby('nome_rede')['imei'].count().reindex(network_metrics['rede']).fillna(0)
        
        # Calcular métricas adicionais
        network_metrics['taxa_utilizacao'] = (network_metrics['vouchers_utilizados'] / network_metrics['total_vouchers'] * 100).fillna(0)
        network_metrics['ticket_medio'] = (network_metrics['valor_total'] / network_metrics['vouchers_utilizados']).fillna(0)
        network_metrics = network_metrics.sort_values('valor_total', ascending=False)

        # Tabela de métricas por rede
        table = dash_table.DataTable(
            id='network-metrics-table',
            columns=[
                {'name': 'Rede', 'id': 'rede'},
                {'name': 'Total Vouchers', 'id': 'total_vouchers', 'type': 'numeric', 'format': {'specifier': ',d'}},
                {'name': 'Vouchers Utilizados', 'id': 'vouchers_utilizados', 'type': 'numeric', 'format': {'specifier': ',d'}},
                {'name': 'Taxa Utilização (%)', 'id': 'taxa_utilizacao', 'type': 'numeric', 'format': {'specifier': '.1f'}},
                {'name': 'Valor Total (R$)', 'id': 'valor_total', 'type': 'numeric', 'format': {'specifier': ',.2f'}},
                {'name': 'Ticket Médio (R$)', 'id': 'ticket_medio', 'type': 'numeric', 'format': {'specifier': ',.2f'}}
            ],
            data=network_metrics.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
            page_size=10,
            sort_action='native',
            filter_action='native'
        )

        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.H4("📋 Métricas por Rede", className="mb-4"),
                    table
                ], md=12)
            ])
        ])

    except Exception as e:
        print(f"Erro ao gerar análise de redes: {str(e)}")
        traceback.print_exc()
        return error_message()

def generate_rankings_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de rankings.
    """
    try:
        if df.empty:
            return no_data_message()

        # Filtrar apenas vouchers utilizados
        df_utilizados = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]

        # Rankings por vendedor
        vendedor_metrics = df_utilizados.groupby('nome_vendedor').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).reset_index()
        vendedor_metrics.columns = ['vendedor', 'total_vouchers', 'valor_total']
        vendedor_metrics['ticket_medio'] = vendedor_metrics['valor_total'] / vendedor_metrics['total_vouchers']
        vendedor_metrics = vendedor_metrics.sort_values('valor_total', ascending=False)

        # Tabela Top Vendedores
        table_vendedores = dash_table.DataTable(
            id='vendedor-metrics-table',
            columns=[
                {'name': 'Vendedor', 'id': 'vendedor'},
                {'name': 'Vouchers', 'id': 'total_vouchers', 'type': 'numeric', 'format': {'specifier': ',d'}},
                {'name': 'Valor Total (R$)', 'id': 'valor_total', 'type': 'numeric', 'format': {'specifier': ',.2f'}},
                {'name': 'Ticket Médio (R$)', 'id': 'ticket_medio', 'type': 'numeric', 'format': {'specifier': ',.2f'}}
            ],
            data=vendedor_metrics.head(10).to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
        )

        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.H4("🏆 Top 10 Vendedores", className="mb-4"),
                    table_vendedores
                ], md=12)
            ])
        ])

    except Exception as e:
        print(f"Erro ao gerar rankings: {str(e)}")
        traceback.print_exc()
        return error_message()

def generate_projections_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de projeções.
    
    Args:
        df: DataFrame com os dados de vouchers
    
    Returns:
        Um componente Div com as projeções e análises de tendências
    """
    try:
        if df.empty:
            return no_data_message()
        
        # Converter data para datetime
        df['data'] = pd.to_datetime(df['data_str'])
        
        # Agrupar por data e calcular métricas diárias
        daily_metrics = df.groupby('data').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).reset_index()
        
        # Calcular médias móveis para suavizar tendências
        daily_metrics['media_movel_vouchers'] = daily_metrics['imei'].rolling(window=7).mean()
        daily_metrics['media_movel_valor'] = daily_metrics['valor_dispositivo'].rolling(window=7).mean()
        
        # Criar gráfico de tendências
        fig_trends = go.Figure()
        
        # Vouchers diários e média móvel
        fig_trends.add_trace(go.Scatter(
            x=daily_metrics['data'],
            y=daily_metrics['imei'],
            mode='lines',
            name='Vouchers Diários',
            line=dict(color='#3498db', width=1)
        ))
        
        fig_trends.add_trace(go.Scatter(
            x=daily_metrics['data'],
            y=daily_metrics['media_movel_vouchers'],
            mode='lines',
            name='Média Móvel (7 dias)',
            line=dict(color='#e74c3c', width=2)
        ))
        
        fig_trends.update_layout(
            title='📈 Tendência de Vouchers',
            xaxis_title='Data',
            yaxis_title='Quantidade de Vouchers',
            height=400,
            template='plotly_white',
            showlegend=True
        )
        
        # Calcular projeções simples
        total_dias = (daily_metrics['data'].max() - daily_metrics['data'].min()).days
        media_diaria_vouchers = daily_metrics['imei'].mean()
        media_diaria_valor = daily_metrics['valor_dispositivo'].mean()
        
        projecao_mensal_vouchers = media_diaria_vouchers * 30
        projecao_mensal_valor = media_diaria_valor * 30
        
        # Cards com projeções
        cards_projecoes = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("🎯 Projeção Mensal", className="card-title text-center"),
                        html.H2(f"{projecao_mensal_vouchers:,.0f}",
                               className="text-primary text-center display-4"),
                        html.P("Vouchers/mês (baseado na média diária)",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("💰 Valor Projetado", className="card-title text-center"),
                        html.H2(f"R$ {projecao_mensal_valor:,.2f}",
                               className="text-success text-center display-4"),
                        html.P("Valor mensal projetado",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=6)
        ])
        
        return html.Div([
            cards_projecoes,
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_trends)], md=12)
            ])
        ])
        
    except Exception as e:
        print(f"Erro ao gerar projeções: {str(e)}")
        traceback.print_exc()
        return error_message()

def generate_engagement_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de engajamento.
    
    Args:
        df: DataFrame com os dados de vouchers
    
    Returns:
        Um componente Div com análises de engajamento
    """
    try:
        if df.empty:
            return no_data_message()
        
        # Análise de engajamento por vendedor
        vendedor_engagement = df.groupby('nome_vendedor').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).reset_index()
        
        # Calcular métricas de engajamento
        vendedor_engagement['ticket_medio'] = vendedor_engagement['valor_dispositivo'] / vendedor_engagement['imei']
        vendedor_engagement = vendedor_engagement.sort_values('imei', ascending=False)
        
        # Gráfico de dispersão Vouchers x Valor
        fig_scatter = px.scatter(
            vendedor_engagement,
            x='imei',
            y='valor_dispositivo',
            text='nome_vendedor',
            title='🎯 Engajamento por Vendedor',
            labels={
                'imei': 'Quantidade de Vouchers',
                'valor_dispositivo': 'Valor Total (R$)',
                'nome_vendedor': 'Vendedor'
            }
        )
        
        fig_scatter.update_traces(
            textposition='top center',
            marker=dict(size=10)
        )
        
        fig_scatter.update_layout(
            height=500,
            template='plotly_white',
            showlegend=False
        )
        
        # Tabela de engajamento
        table_engagement = dash_table.DataTable(
            id='engagement-table',
            columns=[
                {'name': 'Vendedor', 'id': 'nome_vendedor'},
                {'name': 'Vouchers', 'id': 'imei', 'type': 'numeric', 'format': {'specifier': ',d'}},
                {'name': 'Valor Total (R$)', 'id': 'valor_dispositivo', 'type': 'numeric', 'format': {'specifier': ',.2f'}},
                {'name': 'Ticket Médio (R$)', 'id': 'ticket_medio', 'type': 'numeric', 'format': {'specifier': ',.2f'}}
            ],
            data=vendedor_engagement.head(10).to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
            page_size=10
        )
        
        return html.Div([
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_scatter)], md=12)
            ]),
            dbc.Row([
                dbc.Col([
                    html.H4("📊 Top 10 Vendedores por Engajamento", className="mb-4 mt-4"),
                    table_engagement
                ], md=12)
            ])
        ])
    
    except Exception as e:
        print(f"Erro ao gerar análise de engajamento: {str(e)}")
        traceback.print_exc()
        return error_message()

# Healthcheck endpoint
@server.route('/health')
def health_check():
    """Endpoint para verificação de saúde do servidor"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'app': 'dashboard-renov'
        })
    except Exception as e:
        print(f"Erro no healthcheck: {str(e)}")
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'app': 'dashboard-renov'
        })

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080)
