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
warnings.filterwarnings('ignore')

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("📊 Dashboard de Performance Renov", 
                   className="text-center mb-4", 
                   style={'color': '#2c3e50', 'fontWeight': 'bold'}),
            html.Hr(style={'borderColor': '#3498db', 'borderWidth': '2px'})
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dcc.Upload(
                id="upload-data",
                children=dbc.Button([
                    html.I(className="fas fa-upload me-2"),
                    "📁 Importar Planilha Base"
                ], color="primary", size="lg", className="w-100"),
                accept=".xlsx,.xls",
                multiple=False,
                style={'width': '100%'}
            )
        ], md=8),
        dbc.Col([
            dbc.Button([
                html.I(className="fas fa-file-pdf me-2"),
                "🖨️ Exportar PDF"
            ], id="export-pdf", color="success", size="lg", className="w-100", disabled=True)
        ], md=4)
    ], className="mb-4"),

    html.Div(id='alerts'),
    dcc.Store(id='store-data'),
    dcc.Store(id='store-filtered-data'),

    html.Div(id='welcome-message', children=[
        dbc.Alert([
            html.I(className="fas fa-cloud-upload-alt fa-3x mb-3"),
            html.H4("Bem-vindo ao Dashboard de Performance Renov!"),
            html.P("Carregue uma planilha Excel (.xlsx) para começar a análise estratégica.")
        ], color="info", className="text-center py-5")
    ]),

    html.Div(id='filters-section', style={'display': 'none'}, children=[
        dbc.Card([
            dbc.CardHeader(html.H5("🔍 Filtros de Análise", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Período:", className="fw-bold mb-1"),
                        dcc.Dropdown(id='filter-month', options=[], multi=True, placeholder="Selecione os meses...")
                    ], md=3),
                    dbc.Col([
                        html.Label("Rede:", className="fw-bold mb-1"),
                        dcc.Dropdown(id='filter-network', options=[], multi=True, placeholder="Selecione as redes...")
                    ], md=3),
                    dbc.Col([
                        html.Label("Situação:", className="fw-bold mb-1"),
                        dcc.Dropdown(id='filter-status', options=[], multi=True, placeholder="Selecione situações...")
                    ], md=3),
                    dbc.Col([
                        html.Label("Ações:", className="fw-bold mb-1"),
                        dbc.Button("🔄 Limpar", id="clear-filters", color="outline-secondary", size="sm", className="w-100")
                    ], md=3)
                ])
            ])
        ], className="mb-4")
    ]),
    
    html.Div(id='kpi-section'),
    
    html.Div(id='tabs-section', style={'display': 'none'}, children=[
        dcc.Tabs(id="main-tabs", value="overview", children=[
            dcc.Tab(label="📈 Visão Geral", value="overview"),
            dcc.Tab(label="🏪 Redes", value="networks"),
            dcc.Tab(label="🏆 Rankings", value="rankings"),
            dcc.Tab(label="🔮 Projeções", value="projections")
        ], className="mb-3")
    ]),
    
    html.Div(id='tab-content-area')

], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'padding': '20px'})

def generate_kpi_cards(df):
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
        
        # NOVO: Gráfico de barras - top redes (apenas utilizados)
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
        
        # Gráfico de evolução diária (movido da aba Temporal)
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
        
        # Ordenar por vouchers utilizados (valor numérico para ordenação)
        network_summary = sorted(network_summary, key=lambda x: int(x['Vouchers_Utilizados']), reverse=True)
        
        # Tabela com formatação corrigida
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
            hover_name='nome_rede',
            title="💰 Performance das Redes"
        )
        fig_scatter.update_layout(height=400)
        
        return dbc.Row([
            dbc.Col([dcc.Graph(figure=fig_scatter)], md=12)
        ])
    except Exception as e:
        return dbc.Alert(f"Erro na análise de redes: {str(e)}", color="danger")

def generate_rankings_content(df):
    try:
        if df.empty:
            return dbc.Alert("Dados não disponíveis para rankings.", color="warning")
        
        store_stats = df.groupby(['nome_filial', 'nome_rede']).agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).round(2)
        store_stats.columns = ['Total_Vouchers', 'Valor_Total']
        store_stats = store_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(25)
        
        return html.Div([
            html.H5("🏪 Ranking das Lojas (Top 25)", className="mb-3"),
            dash_table.DataTable(
                data=store_stats.to_dict('records'),
                columns=[
                    {"name": "Loja", "id": "nome_filial"},
                    {"name": "Rede", "id": "nome_rede"},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric"},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric"}
                ],
                style_cell={"textAlign": "left"},
                style_header={"backgroundColor": "#e74c3c", "color": "white"},
                page_size=25,
                sort_action="native"
            )
        ])
    except Exception as e:
        return dbc.Alert(f"Erro nos rankings: {str(e)}", color="danger")

def generate_projections_content(original_df, filtered_df):
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
        
        return html.Div([
            html.H4("🔮 Projeções e Análise Detalhada", className="mb-4"),
            html.P(f"Período analisado: {unique_days_month} dias de {pd.Timestamp(current_year, current_month, 1).strftime('%B %Y')}", 
                   className="text-muted mb-4"),
            metrics_cards
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro nas projeções: {str(e)}", color="danger")

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
            'imei': ['imei', 'device_id'],
            'criado_em': ['criado_em', 'data_criacao'],
            'valor_voucher': ['valor_do_voucher', 'valor_voucher'],
            'valor_dispositivo': ['valor_do_dispositivo', 'valor_dispositivo'],
            'situacao_voucher': ['situacao_do_voucher', 'situacao_voucher'],
            'nome_vendedor': ['nome_do_vendedor', 'vendedor'],
            'nome_filial': ['nome_da_filial', 'filial'],
            'nome_rede': ['nome_da_rede', 'rede']
        }

        for standard_name, possible_names in required_columns.items():
            for possible_name in possible_names:
                if possible_name in df.columns:
                    column_mapping[possible_name] = standard_name
                    break

        df = df.rename(columns=column_mapping)

        if 'criado_em' in df.columns:
            df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
            df = df.dropna(subset=['criado_em'])
            df['mes'] = df['criado_em'].dt.strftime('%b')
            df['ano'] = df['criado_em'].dt.year
            df['data_str'] = df['criado_em'].dt.strftime('%Y-%m-%d')

        if 'valor_voucher' in df.columns:
            df['valor_voucher'] = pd.to_numeric(df['valor_voucher'], errors='coerce').fillna(0)
        if 'valor_dispositivo' in df.columns:
            df['valor_dispositivo'] = pd.to_numeric(df['valor_dispositivo'], errors='coerce').fillna(0)

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
        
        if active_tab == "overview":
            return generate_overview_content(df)
        elif active_tab == "networks":
            return generate_networks_content(df)
        elif active_tab == "rankings":
            return generate_rankings_content(df)
        elif active_tab == "projections":
            original_df = pd.DataFrame(original_data) if original_data else df
            return generate_projections_content(original_df, df)
        else:
            return html.Div("Aba não encontrada")
    except Exception as e:
        return dbc.Alert(f"Erro: {str(e)}", color="danger")

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 8080)), host='0.0.0.0')