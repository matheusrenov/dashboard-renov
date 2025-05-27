import os
import base64
import io
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from unidecode import unidecode
import warnings
from models import UserDatabase
from auth_layout import create_login_layout, create_register_layout, create_admin_approval_layout
from dash.exceptions import PreventUpdate
from dash.dependencies import no_update
warnings.filterwarnings('ignore')

# ========================
# 🚀 Inicialização do App
# ========================
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
server = app.server

# Inicializa o banco de dados
db = UserDatabase()

# ========================
# 🔐 Layout Principal
# ========================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
    html.Div(id='auth-status')
])

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
            ], width=8),
            dbc.Col([
                html.Div([
                    dbc.Button("Aprovar Usuários", id="show-approvals", 
                              color="success", className="me-2",
                              style={'display': 'inline' if is_super_admin else 'none'}),
                    dbc.Button("Sair", id="logout-button", color="danger")
                ], className="d-flex justify-content-end")
            ], width=4),
            html.Hr(style={'borderColor': '#3498db', 'borderWidth': '2px'})
        ]),
        
        # Conteúdo do Dashboard
        html.Div(id='dashboard-content', className="mt-4"),
        
        # Seção de Aprovação (visível apenas para super admin)
        dbc.Collapse(
            create_admin_approval_layout(),
            id="approval-section",
            is_open=False
        )
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
                    html.Small(f"{(active_stores/total_stores*100):.1f}% do total" if total_stores > 0 else "0% do total", className="text-muted")
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

def update_pending_users_table():
    pending_users = db.get_pending_users()
    if not pending_users:
        return html.Div("Nenhum usuário pendente de aprovação.", className="text-muted")
    
    return dash_table.DataTable(
        id='pending-users',
        data=pending_users,
        columns=[
            {'name': 'Usuário', 'id': 'username'},
            {'name': 'Email', 'id': 'email'},
            {'name': 'Data de Registro', 'id': 'created_at'}
        ],
        style_cell={'textAlign': 'left', 'padding': '10px'},
        style_header={
            'backgroundColor': '#3498db',
            'color': 'white',
            'fontWeight': 'bold'
        }
    )

# ========================
# 📥 CALLBACK DE UPLOAD - Processa dados e popula filtros
# ========================
@app.callback(
    [Output('alerts', 'children'),
     Output('store-data', 'data'),
     Output('export-pdf', 'disabled'),
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
        return "", {}, True, {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, [], [], []

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        if df.empty:
            return (dbc.Alert("❌ Arquivo vazio!", color="danger"), {}, True, 
                   {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, [], [], [])

        df.columns = [unidecode(str(col)).strip().lower().replace(' ', '_').replace('ç', 'c') for col in df.columns]
        
        column_mapping = {}
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
            return (
                dbc.Alert(f"❌ Colunas obrigatórias não encontradas: {', '.join(missing_columns)}", color="danger"),
                {}, True, {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, [], [], []
            )

        # Renomear colunas
        df = df.rename(columns=column_mapping)

        # Processar dados
        if 'criado_em' in df.columns:
            df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
            df = df.dropna(subset=['criado_em'])
            df['mes'] = df['criado_em'].dt.strftime('%b')
            df['mes_num'] = df['criado_em'].dt.month
            df['dia'] = df['criado_em'].dt.day
            df['ano'] = df['criado_em'].dt.year
            df['data_str'] = df['criado_em'].dt.strftime('%Y-%m-%d')

        if df.empty:
            return (dbc.Alert("❌ Nenhuma data válida encontrada!", color="danger"), {}, True,
                   {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, [], [], [])

        # Limpar dados numéricos
        if 'valor_voucher' in df.columns:
            df['valor_voucher'] = pd.to_numeric(df['valor_voucher'], errors='coerce').fillna(0)
        if 'valor_dispositivo' in df.columns:
            df['valor_dispositivo'] = pd.to_numeric(df['valor_dispositivo'], errors='coerce').fillna(0)

        # Preparar opções para filtros
        month_options = []
        network_options = []
        status_options = []
        
        if 'mes' in df.columns and 'ano' in df.columns:
            month_options = [
                {'label': f"{month} ({year})", 'value': f"{month}_{year}"} 
                for month, year in df.groupby(['mes', 'ano']).size().index
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

        # Sucesso
        success_alert = dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"✅ Arquivo '{filename}' processado com sucesso! {len(df)} registros carregados."
        ], color="success", dismissable=True)

        return (success_alert, df.to_dict('records'), False,
               {'display': 'none'}, {'display': 'block'}, {'display': 'block'},
               month_options, network_options, status_options)

    except Exception as e:
        return (
            dbc.Alert(f"❌ Erro ao processar arquivo: {str(e)}", color="danger"),
            {}, True, {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, [], [], []
        )

# ========================
# 🔄 CALLBACK PARA APLICAR FILTROS
# ========================
@app.callback(
    Output('store-filtered-data', 'data'),
    [Input('filter-month', 'value'),
     Input('filter-network', 'value'),
     Input('filter-status', 'value'),
     Input('clear-filters', 'n_clicks')],
    [State('store-data', 'data')],
    prevent_initial_call=True
)
def apply_filters(months, networks, statuses, clear_clicks, original_data):
    if not original_data:
        return {}
    
    ctx = callback_context
    if ctx.triggered and 'clear-filters' in ctx.triggered[0]['prop_id']:
        return original_data
    
    df = pd.DataFrame(original_data)
    
    if months and 'mes' in df.columns and 'ano' in df.columns:
        month_year_filters = [f"{row['mes']}_{row['ano']}" for _, row in df.iterrows()]
        df = df[[mf in months for mf in month_year_filters]]
    
    if networks and 'nome_rede' in df.columns:
        df = df[df['nome_rede'].isin(networks)]
    
    if statuses and 'situacao_voucher' in df.columns:
        df = df[df['situacao_voucher'].isin(statuses)]
    
    return df.to_dict('records')

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
    data_to_use = filtered_data if filtered_data else original_data
    if not data_to_use:
        return html.Div()
    
    df = pd.DataFrame(data_to_use)
    return generate_kpi_cards(df)

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
# 🔄 Callbacks de Autenticação
# ========================
@app.callback(
    [Output('auth-status', 'children', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True),
     Output('page-content', 'children', allow_duplicate=True)],
    [Input('login-button', 'n_clicks'),
     Input('register-button', 'n_clicks'),
     Input('url', 'pathname')],
    [State('login-username', 'value'),
     State('login-password', 'value'),
     State('register-username', 'value'),
     State('register-email', 'value'),
     State('register-password', 'value'),
     State('register-confirm-password', 'value')],
    prevent_initial_call=True
)
def handle_auth_final(login_clicks, register_clicks, pathname,
                     username, password, reg_username, reg_email,
                     reg_password, reg_confirm_password):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if triggered_id == 'login-button' and username and password:
        user = db.verify_user(username, password)
        if user:
            if not user['is_approved']:
                return (
                    dbc.Alert("Sua conta ainda está pendente de aprovação.", color="warning", className="mt-3"),
                    "/",
                    create_login_layout()
                )
            is_super_admin = user['email'] == 'matheus@renovsmart.com.br'
            return "", "/dashboard", create_dashboard_layout(is_super_admin)
        return (
            dbc.Alert("Usuário ou senha inválidos.", color="danger", className="mt-3"),
            "/",
            create_login_layout()
        )
    
    if triggered_id == 'register-button':
        if not all([reg_username, reg_email, reg_password, reg_confirm_password]):
            return (
                dbc.Alert("Todos os campos são obrigatórios.", color="danger", className="mt-3"),
                "/register",
                create_register_layout()
            )
        
        if reg_password != reg_confirm_password:
            return (
                dbc.Alert("As senhas não coincidem.", color="danger", className="mt-3"),
                "/register",
                create_register_layout()
            )
        
        if db.create_user(reg_username, reg_password, reg_email):
            return (
                dbc.Alert("Conta criada com sucesso! Aguarde a aprovação do administrador.", color="success", className="mt-3"),
                "/",
                create_login_layout()
            )
        return (
            dbc.Alert("Usuário ou email já existem.", color="danger", className="mt-3"),
            "/register",
            create_register_layout()
        )
    
    # Handle URL changes
    if triggered_id == 'url':
        if pathname == "/dashboard":
            return "", pathname, create_dashboard_layout()
        elif pathname == "/register":
            return "", pathname, create_register_layout()
        return "", "/", create_login_layout()
    
    raise PreventUpdate

@app.callback(
    [Output('auth-status', 'children', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True),
     Output('page-content', 'children', allow_duplicate=True)],
    [Input('show-register', 'n_clicks'),
     Input('show-login', 'n_clicks'),
     Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_nav_final(show_reg_clicks, show_login_clicks, logout_clicks):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if triggered_id == 'show-register':
        return "", "/register", create_register_layout()
    elif triggered_id == 'show-login':
        return "", "/", create_login_layout()
    elif triggered_id == 'logout-button':
        return "", "/", create_login_layout()
    
    raise PreventUpdate

@app.callback(
    Output('pending-users-table', 'children'),
    [Input('url', 'pathname')]
)
def update_pending_users(pathname):
    if pathname != "/dashboard":
        return html.Div()
    
    return update_pending_users_table()

@app.callback(
    Output('pending-users-table', 'children'),
    [Input('approve-user-button', 'n_clicks'),
     Input('reject-user-button', 'n_clicks')],
    [State('pending-users-table', 'selected_rows'),
     State('pending-users-table', 'data')]
)
def handle_user_approval(approve_clicks, reject_clicks, selected_rows, table_data):
    if not selected_rows:
        return dash.no_update
    
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    selected_user = table_data[selected_rows[0]]
    
    if triggered_id == 'approve-user-button':
        db.approve_user(selected_user['email'])
    elif triggered_id == 'reject-user-button':
        db.reject_user(selected_user['email'])
    
    return update_pending_users_table()

@app.callback(
    Output('approval-section', 'is_open'),
    [Input('show-approvals', 'n_clicks')],
    [State('approval-section', 'is_open')]
)
def toggle_approval_section(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output('dashboard-content', 'children'),
    [Input('url', 'pathname')]
)
def update_content(pathname):
    if pathname == "/dashboard":
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Arraste e solte ou ',
                            html.A('selecione um arquivo', className="text-primary")
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
                        }
                    ),
                    html.Div(id='alerts'),
                    html.Div(id='welcome-message', children=[
                        html.H4("👋 Bem-vindo ao Dashboard!", className="text-center mt-5"),
                        html.P("Faça o upload de um arquivo para começar.", className="text-center text-muted")
                    ]),
                    dcc.Store(id='store-data'),
                    dcc.Store(id='store-filtered-data')
                ])
            ]),
            
            # Seção de Filtros
            html.Div(id='filters-section', style={'display': 'none'}, children=[
                dbc.Row([
                    dbc.Col([
                        html.H5("🔍 Filtros", className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                html.Label("Mês:"),
                                dcc.Dropdown(id='filter-month', multi=True)
                            ], md=4),
                            dbc.Col([
                                html.Label("Rede:"),
                                dcc.Dropdown(id='filter-network', multi=True)
                            ], md=4),
                            dbc.Col([
                                html.Label("Situação:"),
                                dcc.Dropdown(id='filter-status', multi=True)
                            ], md=4)
                        ]),
                        dbc.Button("Limpar Filtros", id="clear-filters", 
                                 color="secondary", size="sm", className="mt-2")
                    ])
                ], className="mb-4")
            ]),
            
            # Seção de KPIs
            html.Div(id='kpi-section'),
            
            # Seção de Tabs
            html.Div(id='tabs-section', style={'display': 'none'}, children=[
                dcc.Tabs(id='main-tabs', value='overview', children=[
                    dcc.Tab(label='Visão Geral', value='overview'),
                    dcc.Tab(label='Redes', value='networks'),
                    dcc.Tab(label='Rankings', value='rankings'),
                    dcc.Tab(label='Projeções', value='projections')
                ], className="mb-4"),
                html.Div(id='tab-content-area')
            ])
        ])
    return html.Div()

# ========================
# 🔚 Execução
# ========================
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 8080)), host='0.0.0.0')