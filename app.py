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

# Módulos locais
from models import UserDatabase
from models_network import NetworkDatabase
from auth_layout import create_login_layout, create_register_layout, create_admin_approval_layout
from error_layout import create_error_layout

# Configuração dos assets
assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
if not os.path.exists(assets_path):
    os.makedirs(assets_path)

# Inicialização do Flask
server = Flask(__name__)
CORS(server)

# Configurações do Flask
server.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(16)),
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///database.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

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

# Layout inicial
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Callback para roteamento de páginas
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/login' or pathname == '/':
        return create_login_layout()
    elif pathname == '/dashboard':
        return create_dashboard_layout()
    else:
        return create_error_layout('404')

# Callback de autenticação
@app.callback(
    [
        Output('url', 'pathname'),
        Output('login-error', 'children')
    ],
    [
        Input('login-button', 'n_clicks')
    ],
    [
        State('login-username', 'value'),
        State('login-password', 'value')
    ],
    prevent_initial_call=True
)
def authenticate(n_clicks, username, password):
    if not n_clicks:
        return no_update, no_update
    
    if not username or not password:
        return no_update, html.Div('Por favor, preencha todos os campos', style={'color': 'red'})
    
    try:
        user_db = UserDatabase()
        user = user_db.verify_user(username, password)
        
        if user:
            return '/dashboard', no_update
        else:
            return no_update, html.Div('Usuário ou senha inválidos', style={'color': 'red'})
    except Exception as e:
        print(f"Erro na autenticação: {str(e)}")
        return no_update, html.Div('Erro ao tentar fazer login. Tente novamente.', style={'color': 'red'})

# Callback de logout
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('logout-button', 'n_clicks'),
    prevent_initial_call=True
)
def logout(n_clicks):
    if n_clicks:
        return '/login'
    return no_update

# Inicialização das extensões
db = SQLAlchemy(server)

# ========================
# 📊 Layout do Dashboard
# ========================

def create_dashboard_layout(is_super_admin=False):
    """
    Cria o layout principal do dashboard.
    
    Args:
        is_super_admin: Se o usuário é um super administrador
    
    Returns:
        Um componente Container com o layout do dashboard
    """
    return dbc.Container([
        # Cabeçalho
        dbc.Row([
            dbc.Col([
                html.H1("Dashboard Renov", className="mb-4"),
                dbc.Button(
                    "Sair",
                    id="logout-button",
                    color="danger",
                    className="float-end"
                )
            ])
        ], className="mb-4"),

        # Status do sistema
        dbc.Row([
            dbc.Col([
                html.Div(id="system-health"),
                dcc.Interval(
                    id='health-interval',
                    interval=30000,  # 30 segundos
                    n_intervals=0
                )
            ])
        ], className="mb-4"),

        # Upload de dados
        dbc.Row([
            dbc.Col([
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        '📊 Upload de Dados'
                    ], className="text-center p-3 border rounded"),
                    className="mb-3"
                ),
                html.Div(id='upload-status')
            ], md=6),
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        dcc.Upload(
                            id='upload-networks-branches-file',
                            children=html.Div([
                                '🏪 Upload de Redes/Filiais'
                            ], className="text-center p-3 border rounded"),
                            className="mb-3"
                        )
                    ], md=6),
                    dbc.Col([
                        dcc.Upload(
                            id='upload-employees-file',
                            children=html.Div([
                                '👥 Upload de Colaboradores'
                            ], className="text-center p-3 border rounded"),
                            className="mb-3"
                        )
                    ], md=6)
                ]),
                html.Div(id='network-upload-status')
            ], md=6)
        ], className="mb-4"),

        # Mensagem de boas-vindas
        html.Div([
            dbc.Alert([
                html.H4("👋 Bem-vindo ao Dashboard Renov!", className="alert-heading"),
                html.P([
                    "Para começar, faça o upload do arquivo de dados usando o botão acima. ",
                    "O arquivo deve estar no formato Excel (.xls ou .xlsx) e conter as seguintes colunas:"
                ]),
                html.Hr(),
                html.P([
                    "Colunas obrigatórias:",
                    html.Ul([
                        html.Li("IMEI ou Device ID"),
                        html.Li("Data de Criação"),
                        html.Li("Valor do Voucher"),
                        html.Li("Valor do Dispositivo"),
                        html.Li("Situação do Voucher"),
                        html.Li("Nome do Vendedor"),
                        html.Li("Nome da Filial"),
                        html.Li("Nome da Rede")
                    ])
                ], className="mb-0")
            ], color="info", id="welcome-message")
        ], className="mb-4"),

        # Seção de filtros
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.H4("🔍 Filtros", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Mês"),
                            dcc.Dropdown(
                                id='filter-month',
                                options=[],
                                placeholder="Selecione o mês",
                                multi=True
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Rede"),
                            dcc.Dropdown(
                                id='filter-network',
                                options=[],
                                value='todas',
                                placeholder="Selecione a rede"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Status"),
                            dcc.Dropdown(
                                id='filter-status',
                                options=[],
                                value='todos',
                                placeholder="Selecione o status"
                            )
                        ], md=4)
                    ], className="mb-3"),
                    dbc.Button(
                        "Limpar Filtros",
                        id="clear-filters",
                        color="secondary",
                        size="sm"
                    )
                ])
            ])
        ], id="filters-section", style={'display': 'none'}, className="mb-4"),

        # Seção de abas
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div(id='kpi-section', className="mb-4"),
                    dbc.Tabs([
                        dbc.Tab(label="📊 Visão Geral", tab_id="overview"),
                        dbc.Tab(label="🏢 Redes", tab_id="networks"),
                        dbc.Tab(label="🏆 Rankings", tab_id="rankings"),
                        dbc.Tab(label="🔮 Projeções", tab_id="projections"),
                        dbc.Tab(label="👥 Engajamento", tab_id="engagement"),
                        dbc.Tab(label="📋 Base de Redes", tab_id="network-base")
                    ], id="main-tabs", active_tab="overview"),
                    html.Div(id="tab-content-area", className="mt-4")
                ])
            ])
        ], id="tabs-section", style={'display': 'none'}, className="mb-4"),

        # Seção de exportação
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button(
                        "📥 Exportar Excel",
                        id="export-excel",
                        color="success",
                        className="me-2"
                    ),
                    dbc.Button(
                        "📄 Exportar PDF",
                        id="export-pdf",
                        color="primary"
                    )
                ])
            ], className="text-end")
        ]),

        # Componentes ocultos
        dcc.Store(id='store-data'),
        dcc.Store(id='store-filtered-data'),
        dcc.Download(id="download-data")
    ], fluid=True)

# ========================
# 📊 Funções de Geração de Conteúdo
# ========================

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
        return html.Div()

def generate_overview_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de visão geral.
    
    Args:
        df: DataFrame com os dados de vouchers
    
    Returns:
        Um componente Div com a visão geral
    """
    try:
        if df.empty:
            return dbc.Alert("Nenhum dado disponível para análise.", color="warning")

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
            hovermode='x unified',
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Gráfico de distribuição por status
        status_data = df['situacao_voucher'].value_counts()
        fig_status = go.Figure(data=[go.Pie(
            labels=status_data.index,
            values=status_data.values,
            hole=.3,
            marker_colors=['#3498db', '#2ecc71', '#e74c3c', '#f1c40f']
        )])
        fig_status.update_layout(
            title='🔄 Distribuição por Status',
            height=400,
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Gráfico de distribuição por rede
        network_data = df['nome_rede'].value_counts().head(10)
        fig_networks = go.Figure(data=[go.Bar(
            x=network_data.values,
            y=network_data.index,
            orientation='h',
            marker_color='#3498db'
        )])
        fig_networks.update_layout(
            title='🏢 Top 10 Redes',
            xaxis_title='Quantidade de Vouchers',
            height=400,
            template='plotly_white',
            showlegend=False
        )

        return html.Div([
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_evolution)], md=12)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_status)], md=6),
                dbc.Col([dcc.Graph(figure=fig_networks)], md=6)
            ])
        ])

    except Exception as e:
        print(f"Erro ao gerar visão geral: {str(e)}")
        return dbc.Alert(f"Erro ao gerar análise: {str(e)}", color="danger")

def generate_networks_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de redes.
    
    Args:
        df: DataFrame com os dados de vouchers
    
    Returns:
        Um componente Div com a análise de redes
    """
    try:
        if df.empty:
            return dbc.Alert("Nenhum dado disponível para análise de redes.", color="warning")

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
            style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}],
            page_size=10,
            sort_action='native',
            filter_action='native'
        )

        # Gráfico de desempenho por rede
        top_10_networks = network_metrics.head(10)
        fig_performance = go.Figure()
        fig_performance.add_trace(go.Bar(
            name='Valor Total (R$)',
            x=top_10_networks['rede'],
            y=top_10_networks['valor_total'],
            marker_color='#3498db'
        ))
        fig_performance.add_trace(go.Scatter(
            name='Taxa de Utilização (%)',
            x=top_10_networks['rede'],
            y=top_10_networks['taxa_utilizacao'],
            mode='lines+markers',
            yaxis='y2',
            line=dict(color='#e74c3c', width=2),
            marker=dict(size=8)
        ))

        fig_performance.update_layout(
            title='📊 Desempenho das Top 10 Redes',
            xaxis_title='Rede',
            yaxis_title='Valor Total (R$)',
            yaxis2=dict(
                title='Taxa de Utilização (%)',
                overlaying='y',
                side='right'
            ),
            height=400,
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            barmode='group'
        )

        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.H4("📋 Métricas por Rede", className="mb-4"),
                    table
                ], md=12, className="mb-4")
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_performance)
                ], md=12)
            ])
        ])

    except Exception as e:
        print(f"Erro ao gerar análise de redes: {str(e)}")
        return dbc.Alert(f"Erro ao gerar análise de redes: {str(e)}", color="danger")

def generate_rankings_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de rankings.
    
    Args:
        df: DataFrame com os dados de vouchers
    
    Returns:
        Um componente Div com os rankings
    """
    try:
        if df.empty:
            return dbc.Alert("Nenhum dado disponível para análise de rankings.", color="warning")

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

        # Rankings por filial
        filial_metrics = df_utilizados.groupby(['nome_rede', 'nome_filial']).agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).reset_index()
        filial_metrics.columns = ['rede', 'filial', 'total_vouchers', 'valor_total']
        filial_metrics['ticket_medio'] = filial_metrics['valor_total'] / filial_metrics['total_vouchers']
        filial_metrics = filial_metrics.sort_values('valor_total', ascending=False)

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
            style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}]
        )

        # Tabela Top Filiais
        table_filiais = dash_table.DataTable(
            id='filial-metrics-table',
            columns=[
                {'name': 'Rede', 'id': 'rede'},
                {'name': 'Filial', 'id': 'filial'},
                {'name': 'Vouchers', 'id': 'total_vouchers', 'type': 'numeric', 'format': {'specifier': ',d'}},
                {'name': 'Valor Total (R$)', 'id': 'valor_total', 'type': 'numeric', 'format': {'specifier': ',.2f'}},
                {'name': 'Ticket Médio (R$)', 'id': 'ticket_medio', 'type': 'numeric', 'format': {'specifier': ',.2f'}}
            ],
            data=filial_metrics.head(10).to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}]
        )

        # Gráfico de Top 10 Vendedores
        top_10_vendedores = vendedor_metrics.head(10)
        fig_vendedores = go.Figure()
        fig_vendedores.add_trace(go.Bar(
            name='Valor Total (R$)',
            x=top_10_vendedores['vendedor'],
            y=top_10_vendedores['valor_total'],
            marker_color='#3498db'
        ))
        fig_vendedores.add_trace(go.Scatter(
            name='Ticket Médio (R$)',
            x=top_10_vendedores['vendedor'],
            y=top_10_vendedores['ticket_medio'],
            mode='lines+markers',
            yaxis='y2',
            line=dict(color='#e74c3c', width=2),
            marker=dict(size=8)
        ))

        fig_vendedores.update_layout(
            title='🏆 Top 10 Vendedores',
            xaxis_title='Vendedor',
            yaxis_title='Valor Total (R$)',
            yaxis2=dict(
                title='Ticket Médio (R$)',
                overlaying='y',
                side='right'
            ),
            height=400,
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.H4("🥇 Top 10 Vendedores", className="mb-4"),
                    table_vendedores
                ], md=12, className="mb-4")
            ]),
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_vendedores)], md=12, className="mb-4")
            ]),
            dbc.Row([
                dbc.Col([
                    html.H4("🏪 Top 10 Filiais", className="mb-4"),
                    table_filiais
                ], md=12)
            ])
        ])

    except Exception as e:
        print(f"Erro ao gerar rankings: {str(e)}")
        return dbc.Alert(f"Erro ao gerar rankings: {str(e)}", color="danger")

def generate_projections_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de projeções.
    
    Args:
        df: DataFrame com os dados de vouchers
    
    Returns:
        Um componente Div com as projeções
    """
    try:
        if df.empty:
            return dbc.Alert("Nenhum dado disponível para análise de projeções.", color="warning")

        # Preparar dados para projeção
        df['data'] = pd.to_datetime(df['data_str'])
        df_utilizados = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        
        # Análise diária
        daily_data = df_utilizados.groupby('data').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).reset_index()
        daily_data.columns = ['data', 'vouchers', 'valor']

        # Calcular médias móveis
        daily_data['mm_7d_vouchers'] = daily_data['vouchers'].rolling(window=7, min_periods=1).mean()
        daily_data['mm_7d_valor'] = daily_data['valor'].rolling(window=7, min_periods=1).mean()
        daily_data['mm_30d_vouchers'] = daily_data['vouchers'].rolling(window=30, min_periods=1).mean()
        daily_data['mm_30d_valor'] = daily_data['valor'].rolling(window=30, min_periods=1).mean()

        # Projetar próximos 30 dias
        last_date = daily_data['data'].max()
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=30, freq='D')
        
        # Usar média dos últimos 30 dias para projeção
        avg_vouchers = daily_data['vouchers'].tail(30).mean()
        avg_valor = daily_data['valor'].tail(30).mean()
        
        projection_data = pd.DataFrame({
            'data': future_dates,
            'vouchers': [avg_vouchers] * 30,
            'valor': [avg_valor] * 30,
            'tipo': ['projeção'] * 30
        })

        # Gráfico de projeção de vouchers
        fig_vouchers = go.Figure()
        
        # Dados reais
        fig_vouchers.add_trace(go.Scatter(
            name='Vouchers Diários',
            x=daily_data['data'],
            y=daily_data['vouchers'],
            mode='markers',
            marker=dict(size=6, color='#3498db', opacity=0.5)
        ))
        
        fig_vouchers.add_trace(go.Scatter(
            name='Média Móvel (7 dias)',
            x=daily_data['data'],
            y=daily_data['mm_7d_vouchers'],
            mode='lines',
            line=dict(color='#2ecc71', width=2)
        ))
        
        fig_vouchers.add_trace(go.Scatter(
            name='Média Móvel (30 dias)',
            x=daily_data['data'],
            y=daily_data['mm_30d_vouchers'],
            mode='lines',
            line=dict(color='#e74c3c', width=2)
        ))
        
        # Projeção
        fig_vouchers.add_trace(go.Scatter(
            name='Projeção',
            x=projection_data['data'],
            y=projection_data['vouchers'],
            mode='lines',
            line=dict(color='#f1c40f', width=2, dash='dash')
        ))

        fig_vouchers.update_layout(
            title='📈 Projeção de Vouchers',
            xaxis_title='Data',
            yaxis_title='Quantidade de Vouchers',
            height=400,
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Gráfico de projeção de valor
        fig_valor = go.Figure()
        
        # Dados reais
        fig_valor.add_trace(go.Scatter(
            name='Valor Diário (R$)',
            x=daily_data['data'],
            y=daily_data['valor'],
            mode='markers',
            marker=dict(size=6, color='#3498db', opacity=0.5)
        ))
        
        fig_valor.add_trace(go.Scatter(
            name='Média Móvel (7 dias)',
            x=daily_data['data'],
            y=daily_data['mm_7d_valor'],
            mode='lines',
            line=dict(color='#2ecc71', width=2)
        ))
        
        fig_valor.add_trace(go.Scatter(
            name='Média Móvel (30 dias)',
            x=daily_data['data'],
            y=daily_data['mm_30d_valor'],
            mode='lines',
            line=dict(color='#e74c3c', width=2)
        ))
        
        # Projeção
        fig_valor.add_trace(go.Scatter(
            name='Projeção',
            x=projection_data['data'],
            y=projection_data['valor'],
            mode='lines',
            line=dict(color='#f1c40f', width=2, dash='dash')
        ))

        fig_valor.update_layout(
            title='💰 Projeção de Valor',
            xaxis_title='Data',
            yaxis_title='Valor Total (R$)',
            height=400,
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Calcular métricas de projeção
        projecao_mensal_vouchers = avg_vouchers * 30
        projecao_mensal_valor = avg_valor * 30

        # Cards com métricas de projeção
        cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("📊 Projeção Mensal de Vouchers", className="card-title text-center"),
                        html.H2(f"{projecao_mensal_vouchers:,.0f}",
                               className="text-primary text-center display-4"),
                        html.P(f"Média diária: {avg_vouchers:,.1f}",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("💰 Projeção Mensal de Valor", className="card-title text-center"),
                        html.H2(f"R$ {projecao_mensal_valor:,.2f}",
                               className="text-success text-center display-4"),
                        html.P(f"Média diária: R$ {avg_valor:,.2f}",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=6)
        ])

        return html.Div([
            cards,
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_vouchers)], md=12, className="mb-4")
            ]),
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_valor)], md=12)
            ])
        ])

    except Exception as e:
        print(f"Erro ao gerar projeções: {str(e)}")
        return dbc.Alert(f"Erro ao gerar projeções: {str(e)}", color="danger")

def generate_engagement_content(df: pd.DataFrame) -> html.Div:
    """
    Gera o conteúdo da aba de engajamento.
    
    Args:
        df: DataFrame com os dados de vouchers
    
    Returns:
        Um componente Div com as métricas de engajamento
    """
    try:
        if df.empty:
            return dbc.Alert("Nenhum dado disponível para análise de engajamento.", color="warning")

        # Calcular métricas de engajamento
        total_redes = df['nome_rede'].nunique()
        total_filiais = df.groupby('nome_rede')['nome_filial'].nunique().sum()
        total_vendedores = df['nome_vendedor'].nunique()
        
        # Vendedores ativos (com vouchers utilizados)
        df_utilizados = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
        vendedores_ativos = df_utilizados['nome_vendedor'].nunique()
        taxa_ativacao = (vendedores_ativos / total_vendedores * 100) if total_vendedores > 0 else 0

        # Análise de frequência de vendedores
        freq_vendedores = df_utilizados.groupby('nome_vendedor').size()
        freq_dist = freq_vendedores.value_counts().sort_index()
        
        # Gráfico de distribuição de frequência
        fig_freq = go.Figure(data=[go.Bar(
            x=freq_dist.index,
            y=freq_dist.values,
            marker_color='#3498db'
        )])
        
        fig_freq.update_layout(
            title='📊 Distribuição de Vouchers por Vendedor',
            xaxis_title='Quantidade de Vouchers',
            yaxis_title='Número de Vendedores',
            height=400,
            template='plotly_white',
            showlegend=False
        )

        # Análise temporal de engajamento
        df['data'] = pd.to_datetime(df['data_str'])
        daily_engagement = df_utilizados.groupby('data').agg({
            'nome_vendedor': 'nunique',
            'nome_filial': 'nunique',
            'nome_rede': 'nunique'
        }).reset_index()
        
        # Gráfico de engajamento diário
        fig_engagement = go.Figure()
        
        fig_engagement.add_trace(go.Scatter(
            name='Vendedores Ativos',
            x=daily_engagement['data'],
            y=daily_engagement['nome_vendedor'],
            mode='lines',
            line=dict(color='#3498db', width=2)
        ))
        
        fig_engagement.add_trace(go.Scatter(
            name='Filiais Ativas',
            x=daily_engagement['data'],
            y=daily_engagement['nome_filial'],
            mode='lines',
            line=dict(color='#2ecc71', width=2)
        ))
        
        fig_engagement.add_trace(go.Scatter(
            name='Redes Ativas',
            x=daily_engagement['data'],
            y=daily_engagement['nome_rede'],
            mode='lines',
            line=dict(color='#e74c3c', width=2)
        ))

        fig_engagement.update_layout(
            title='📈 Engajamento Diário',
            xaxis_title='Data',
            yaxis_title='Quantidade',
            height=400,
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Cards com métricas principais
        cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("🏢 Total de Redes", className="card-title text-center"),
                        html.H2(f"{total_redes:,}",
                               className="text-primary text-center display-4"),
                        html.P(f"Com {total_filiais:,} filiais",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("👥 Total de Vendedores", className="card-title text-center"),
                        html.H2(f"{total_vendedores:,}",
                               className="text-success text-center display-4"),
                        html.P(f"{vendedores_ativos:,} vendedores ativos",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("📊 Taxa de Ativação", className="card-title text-center"),
                        html.H2(f"{taxa_ativacao:.1f}%",
                               className="text-info text-center display-4"),
                        html.P("Vendedores com vouchers utilizados",
                              className="text-muted text-center")
                    ])
                ], className="mb-4 shadow-sm")
            ], md=4)
        ])

        return html.Div([
            cards,
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_engagement)], md=12, className="mb-4")
            ]),
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_freq)], md=12)
            ])
        ])

    except Exception as e:
        print(f"Erro ao gerar análise de engajamento: {str(e)}")
        return dbc.Alert(f"Erro ao gerar análise de engajamento: {str(e)}", color="danger")

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080)
