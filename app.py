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

# ========================
# 🚀 Inicialização do App
# ========================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# ========================
# 🎨 Layout Principal - TODOS OS IDs PRESENTES DESDE O INÍCIO
# ========================
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("📊 Dashboard Renov - Análise Estratégica de Parceiros", className="text-center mb-4", 
                   style={'color': '#2c3e50', 'fontWeight': 'bold'}),
            html.Hr(style={'borderColor': '#3498db', 'borderWidth': '2px'})
        ])
    ]),

    # Controles de upload
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

    # Container para alertas
    html.Div(id='alerts'),

    # Stores para dados
    dcc.Store(id='store-data'),
    dcc.Store(id='store-filtered-data'),

    # Estado inicial - aguardando upload
    html.Div(id='welcome-message', children=[
        dbc.Alert([
            html.I(className="fas fa-cloud-upload-alt fa-3x mb-3"),
            html.H4("Bem-vindo ao Dashboard Renov!"),
            html.P("Carregue uma planilha Excel (.xlsx) para começar a análise estratégica dos dados de parceiros.")
        ], color="info", className="text-center py-5")
    ]),

    # FILTROS - SEMPRE PRESENTES NO LAYOUT (inicialmente ocultos)
    html.Div(id='filters-section', style={'display': 'none'}, children=[
        dbc.Card([
            dbc.CardHeader(html.H5("🔍 Filtros de Análise", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Período:", className="fw-bold mb-1"),
                        dcc.Dropdown(
                            id='filter-month',
                            options=[],
                            multi=True,
                            placeholder="Selecione os meses..."
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Rede:", className="fw-bold mb-1"),
                        dcc.Dropdown(
                            id='filter-network',
                            options=[],
                            multi=True,
                            placeholder="Selecione as redes..."
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Situação:", className="fw-bold mb-1"),
                        dcc.Dropdown(
                            id='filter-status',
                            options=[],
                            multi=True,
                            placeholder="Selecione situações..."
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Ações:", className="fw-bold mb-1"),
                        html.Div([
                            dbc.Button("🔄 Limpar", id="clear-filters", color="outline-secondary", size="sm", className="w-100")
                        ])
                    ], md=3)
                ])
            ])
        ], className="mb-4")
    ]),
    
    # KPIs - sempre presente (inicialmente vazio)
    html.Div(id='kpi-section'),
    
    # ABAS - SEMPRE PRESENTES NO LAYOUT (inicialmente ocultas)
    html.Div(id='tabs-section', style={'display': 'none'}, children=[
        dcc.Tabs(id="main-tabs", value="overview", children=[
            dcc.Tab(label="📈 Visão Geral", value="overview"),
            dcc.Tab(label="📅 Temporal", value="temporal"),
            dcc.Tab(label="🏪 Redes", value="networks"),
            dcc.Tab(label="🏆 Rankings", value="rankings"),
            dcc.Tab(label="🔮 Projeções", value="projections")
        ], className="mb-3")
    ]),
    
    # Conteúdo das abas - sempre presente (inicialmente vazio)
    html.Div(id='tab-content-area')

], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'padding': '20px'})

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
        # Decodificar arquivo
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        if df.empty:
            return (dbc.Alert("❌ Arquivo vazio!", color="danger"), {}, True, 
                   {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, [], [], [])

        # Normalizar nomes das colunas
        df.columns = [unidecode(str(col)).strip().lower().replace(' ', '_').replace('ç', 'c') for col in df.columns]
        
        # Mapear colunas essenciais
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
        df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
        df = df.dropna(subset=['criado_em'])
        
        if df.empty:
            return (dbc.Alert("❌ Nenhuma data válida encontrada!", color="danger"), {}, True,
                   {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, [], [], [])

        # Adicionar colunas derivadas
        df['mes'] = df['criado_em'].dt.strftime('%b')
        df['mes_num'] = df['criado_em'].dt.month
        df['dia'] = df['criado_em'].dt.day
        df['ano'] = df['criado_em'].dt.year
        df['data_str'] = df['criado_em'].dt.strftime('%Y-%m-%d')
        df['semana'] = df['criado_em'].dt.isocalendar().week

        # Limpar dados numéricos
        df['valor_voucher'] = pd.to_numeric(df['valor_voucher'], errors='coerce').fillna(0)
        df['valor_dispositivo'] = pd.to_numeric(df['valor_dispositivo'], errors='coerce').fillna(0)

        # Preparar opções para filtros
        month_options = [
            {'label': f"{month} ({year})", 'value': f"{month}_{year}"} 
            for month, year in df.groupby(['mes', 'ano']).size().index
        ]
        
        network_options = [
            {'label': network, 'value': network} 
            for network in sorted(df['nome_rede'].dropna().unique())
        ]
        
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
               {'display': 'none'},  # ocultar welcome
               {'display': 'block'}, # mostrar filtros
               {'display': 'block'}, # mostrar abas
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
    
    if months:
        month_year_filters = [f"{row['mes']}_{row['ano']}" for _, row in df.iterrows()]
        df = df[[mf in months for mf in month_year_filters]]
    
    if networks:
        df = df[df['nome_rede'].isin(networks)]
    
    if statuses:
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
    data_to_use = filtered_data if filtered_data else original_data
    if not data_to_use:
        return html.Div()
    
    df = pd.DataFrame(data_to_use)
    
    if active_tab == "overview":
        return generate_overview_content(df)
    elif active_tab == "temporal":
        return generate_temporal_content(df)
    elif active_tab == "networks":
        return generate_networks_content(df)
    elif active_tab == "rankings":
        return generate_rankings_content(df)
    elif active_tab == "projections":
        original_df = pd.DataFrame(original_data) if original_data else df
        return generate_projections_content(original_df, df)
    
    return html.Div()

# ========================
# 📊 FUNÇÕES DE GERAÇÃO DE CONTEÚDO
# ========================
def generate_kpi_cards(df):
    total_vouchers = len(df)
    used_vouchers = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
    total_used = len(used_vouchers)
    
    total_value = used_vouchers['valor_dispositivo'].sum()
    avg_ticket = total_value / total_used if total_used > 0 else 0
    conversion_rate = (total_used / total_vouchers * 100) if total_vouchers > 0 else 0
    
    # Calcular vouchers únicos por loja
    unique_stores = df['nome_filial'].nunique()
    
    def create_kpi_card(title, value, color="primary", subtitle=""):
        return dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(title, className="card-title text-muted mb-2"),
                    html.H3(value, className=f"text-{color} fw-bold mb-1"),
                    html.Small(subtitle, className="text-muted") if subtitle else html.Div()
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=2)
    
    return dbc.Row([
        create_kpi_card("Vouchers Totais", f"{total_vouchers:,}", "info"),
        create_kpi_card("Vouchers Utilizados", f"{total_used:,}", "success", f"{conversion_rate:.1f}% conversão"),
        create_kpi_card("Valor Total", f"R$ {total_value:,.2f}", "warning"),
        create_kpi_card("Ticket Médio", f"R$ {avg_ticket:,.2f}", "primary"),
        create_kpi_card("Lojas Ativas", f"{unique_stores}", "danger")
    ], className="g-3 mb-4")

def generate_overview_content(df):
    # Gráfico de pizza - distribuição por situação
    status_counts = df['situacao_voucher'].value_counts()
    fig_pie = px.pie(
        values=status_counts.values, 
        names=status_counts.index,
        title="📊 Distribuição por Situação",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(showlegend=True, height=400)
    
    # Gráfico de barras - top redes
    network_counts = df['nome_rede'].value_counts().head(10)
    fig_bar = px.bar(
        x=network_counts.values,
        y=network_counts.index,
        orientation='h',
        title="🏪 Volume por Rede (Top 10)",
        labels={'x': 'Quantidade de Vouchers', 'y': 'Rede'},
        color=network_counts.values,
        color_continuous_scale='viridis'
    )
    fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
    
    return dbc.Row([
        dbc.Col([dcc.Graph(figure=fig_pie)], md=6),
        dbc.Col([dcc.Graph(figure=fig_bar)], md=6)
    ])

def generate_temporal_content(df):
    # Série temporal por dia
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
    fig_line.update_layout(height=400)
    
    # Distribuição por mês
    monthly_counts = df.groupby(['mes', 'ano']).size().reset_index(name='count')
    monthly_counts['periodo'] = monthly_counts['mes'] + '/' + monthly_counts['ano'].astype(str)
    
    fig_monthly = px.bar(
        monthly_counts,
        x='periodo',
        y='count',
        title="📊 Performance Mensal",
        labels={'periodo': 'Período', 'count': 'Quantidade de Vouchers'},
        color='count',
        color_continuous_scale='blues'
    )
    fig_monthly.update_layout(height=400)
    
    # Análise por dia da semana
    df['dia_semana'] = pd.to_datetime(df['data_str']).dt.day_name()
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_counts = df['dia_semana'].value_counts().reindex(weekday_order, fill_value=0)
    
    fig_weekday = px.bar(
        x=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
        y=weekday_counts.values,
        title="📈 Distribuição por Dia da Semana",
        labels={'x': 'Dia da Semana', 'y': 'Quantidade de Vouchers'},
        color=weekday_counts.values,
        color_continuous_scale='greens'
    )
    fig_weekday.update_layout(height=350)
    
    return dbc.Row([
        dbc.Col([dcc.Graph(figure=fig_line)], md=12),
        dbc.Col([dcc.Graph(figure=fig_monthly)], md=8),
        dbc.Col([dcc.Graph(figure=fig_weekday)], md=4)
    ])

def generate_networks_content(df):
    # Análise por rede
    network_analysis = df.groupby('nome_rede').agg({
        'imei': 'count',
        'valor_dispositivo': 'sum',
        'nome_filial': 'nunique'
    }).round(2)
    network_analysis.columns = ['Total_Vouchers', 'Valor_Total', 'Num_Lojas']
    network_analysis['Ticket_Medio'] = (network_analysis['Valor_Total'] / network_analysis['Total_Vouchers']).round(2)
    network_analysis['Vouchers_por_Loja'] = (network_analysis['Total_Vouchers'] / network_analysis['Num_Lojas']).round(1)
    network_analysis = network_analysis.reset_index().sort_values('Total_Vouchers', ascending=False)
    
    # Gráfico scatter
    fig_scatter = px.scatter(
        network_analysis,
        x='Total_Vouchers',
        y='Valor_Total',
        size='Ticket_Medio',
        hover_name='nome_rede',
        title="💰 Performance das Redes: Volume vs Valor Total",
        labels={'Total_Vouchers': 'Total de Vouchers', 'Valor_Total': 'Valor Total (R$)'},
        color='Vouchers_por_Loja',
        color_continuous_scale='viridis'
    )
    fig_scatter.update_layout(height=500)
    
    return dbc.Row([
        dbc.Col([dcc.Graph(figure=fig_scatter)], md=12),
        dbc.Col([
            html.H5("📋 Análise Detalhada por Rede"),
            dash_table.DataTable(
                data=network_analysis.to_dict('records'),
                columns=[
                    {"name": "Rede", "id": "nome_rede"},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric"},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Nº Lojas", "id": "Num_Lojas", "type": "numeric"},
                    {"name": "Ticket Médio", "id": "Ticket_Medio", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Vouchers/Loja", "id": "Vouchers_por_Loja", "type": "numeric", "format": {"specifier": ",.1f"}}
                ],
                style_cell={'textAlign': 'left', 'fontSize': '12px'},
                style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'row_index': 0},
                        'backgroundColor': '#e8f5e8',
                        'color': 'black',
                    }
                ],
                sort_action="native",
                page_size=10
            )
        ], md=12)
    ])

def generate_rankings_content(df):
    # Top vendedores
    seller_stats = df.groupby(['nome_vendedor', 'nome_filial', 'nome_rede']).agg({
        'imei': 'count',
        'valor_dispositivo': 'sum'
    }).round(2)
    seller_stats.columns = ['Total_Vouchers', 'Valor_Total']
    seller_stats['Ticket_Medio'] = (seller_stats['Valor_Total'] / seller_stats['Total_Vouchers']).round(2)
    seller_stats = seller_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(20)
    
    # NOVO: Ranking das Lojas (Filiais)
    store_stats = df.groupby(['nome_filial', 'nome_rede']).agg({
        'imei': 'count',
        'valor_dispositivo': 'sum',
        'nome_vendedor': 'nunique'
    }).round(2)
    store_stats.columns = ['Total_Vouchers', 'Valor_Total', 'Num_Vendedores']
    store_stats['Ticket_Medio'] = (store_stats['Valor_Total'] / store_stats['Total_Vouchers']).round(2)
    store_stats['Vouchers_por_Vendedor'] = (store_stats['Total_Vouchers'] / store_stats['Num_Vendedores']).round(1)
    store_stats = store_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(25)
    
    return dbc.Row([
        # Ranking de Lojas (Filiais)
        dbc.Col([
            html.H5("🏪 Ranking das Lojas (Top 25)", className="mb-3"),
            dash_table.DataTable(
                data=store_stats.to_dict('records'),
                columns=[
                    {"name": "Loja", "id": "nome_filial"},
                    {"name": "Rede", "id": "nome_rede"},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric"},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Nº Vendedores", "id": "Num_Vendedores", "type": "numeric"},
                    {"name": "Ticket Médio", "id": "Ticket_Medio", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Vouchers/Vendedor", "id": "Vouchers_por_Vendedor", "type": "numeric", "format": {"specifier": ",.1f"}}
                ],
                style_cell={'textAlign': 'left', 'fontSize': '11px', 'padding': '8px'},
                style_header={'backgroundColor': '#e74c3c', 'color': 'white', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'row_index': 0},
                        'backgroundColor': '#ffd700',
                        'color': 'black',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {'row_index': 1},
                        'backgroundColor': '#c0c0c0',
                        'color': 'black',
                    },
                    {
                        'if': {'row_index': 2},
                        'backgroundColor': '#cd7f32',
                        'color': 'white',
                    }
                ],
                page_size=25,
                sort_action="native"
            )
        ], md=12, className="mb-4"),
        
        # Ranking de Vendedores
        dbc.Col([
            html.H5("🏆 Ranking dos Vendedores (Top 20)", className="mb-3"),
            dash_table.DataTable(
                data=seller_stats.to_dict('records'),
                columns=[
                    {"name": "Vendedor", "id": "nome_vendedor"},
                    {"name": "Loja", "id": "nome_filial"},
                    {"name": "Rede", "id": "nome_rede"},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric"},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Ticket Médio", "id": "Ticket_Medio", "type": "numeric", "format": {"specifier": ",.2f"}}
                ],
                style_cell={'textAlign': 'left', 'fontSize': '11px', 'padding': '8px'},
                style_header={'backgroundColor': '#28a745', 'color': 'white', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'row_index': 0},
                        'backgroundColor': '#ffd700',
                        'color': 'black',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {'row_index': 1},
                        'backgroundColor': '#c0c0c0',
                        'color': 'black',
                    },
                    {
                        'if': {'row_index': 2},
                        'backgroundColor': '#cd7f32',
                        'color': 'white',
                    }
                ],
                page_size=20,
                sort_action="native"
            )
        ], md=12)
    ])

def generate_projections_content(original_df, filtered_df):
    """Gera análises e projeções baseadas nos dados históricos"""
    
    # Usar dados originais para análise temporal completa
    df = original_df.copy()
    df['criado_em'] = pd.to_datetime(df['criado_em'])
    
    # Identificar o último mês com dados
    last_date = df['criado_em'].max()
    current_month = last_date.month
    current_year = last_date.year
    
    # Análise mensal histórica
    monthly_data = df.groupby([df['criado_em'].dt.year, df['criado_em'].dt.month]).agg({
        'imei': 'count',
        'valor_dispositivo': 'sum'
    }).reset_index()
    monthly_data.columns = ['ano', 'mes', 'total_vouchers', 'valor_total']
    monthly_data['periodo'] = pd.to_datetime(monthly_data[['ano', 'mes']].assign(day=1))
    
    # Filtrar últimos 6 meses para tendência
    six_months_ago = last_date - pd.DateOffset(months=6)
    recent_data = monthly_data[monthly_data['periodo'] >= six_months_ago].copy()
    
    # Calcular métricas do mês atual (em andamento)
    current_month_data = df[
        (df['criado_em'].dt.month == current_month) & 
        (df['criado_em'].dt.year == current_year)
    ]
    
    # Dias decorridos no mês atual
    days_passed = last_date.day
    days_in_month = pd.Timestamp(current_year, current_month, 1).days_in_month
    
    # Projeções baseadas na tendência atual
    current_vouchers = len(current_month_data)
    current_value = current_month_data['valor_dispositivo'].sum()
    
    # Projeção linear simples baseada nos dias decorridos
    projected_vouchers = int((current_vouchers / days_passed) * days_in_month) if days_passed > 0 else 0
    projected_value = (current_value / days_passed) * days_in_month if days_passed > 0 else 0
    
    # Calcular crescimento vs mês anterior
    if len(recent_data) >= 2:
        last_month_vouchers = recent_data.iloc[-2]['total_vouchers']
        last_month_value = recent_data.iloc[-2]['valor_total']
        growth_vouchers = ((projected_vouchers - last_month_vouchers) / last_month_vouchers * 100) if last_month_vouchers > 0 else 0
        growth_value = ((projected_value - last_month_value) / last_month_value * 100) if last_month_value > 0 else 0
    else:
        growth_vouchers = 0
        growth_value = 0
    
    # Cards de projeções
    projection_cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("📊 Vouchers Realizados", className="text-muted mb-2"),
                    html.H4(f"{current_vouchers:,}", className="text-info mb-1"),
                    html.Small(f"até {last_date.strftime('%d/%m')}", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("🔮 Projeção Mensal", className="text-muted mb-2"),
                    html.H4(f"{projected_vouchers:,}", className="text-primary mb-1"),
                    html.Small(f"{growth_vouchers:+.1f}% vs mês anterior", 
                             className=f"text-{'success' if growth_vouchers >= 0 else 'danger'}")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("💰 Valor Realizado", className="text-muted mb-2"),
                    html.H4(f"R$ {current_value:,.0f}", className="text-warning mb-1"),
                    html.Small(f"até {last_date.strftime('%d/%m')}", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("💎 Projeção Valor", className="text-muted mb-2"),
                    html.H4(f"R$ {projected_value:,.0f}", className="text-success mb-1"),
                    html.Small(f"{growth_value:+.1f}% vs mês anterior", 
                             className=f"text-{'success' if growth_value >= 0 else 'danger'}")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("⏱️ Progresso do Mês", className="text-muted mb-2"),
                    html.H4(f"{(days_passed/days_in_month*100):.0f}%", className="text-danger mb-1"),
                    html.Small(f"{days_passed}/{days_in_month} dias", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("📈 Performance Diária", className="text-muted mb-2"),
                    html.H4(f"{(current_vouchers/days_passed):.0f}" if days_passed > 0 else "0", className="text-info mb-1"),
                    html.Small("vouchers/dia média", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=2)
    ], className="g-3 mb-4")
    
    # Gráfico de tendência com projeção
    fig_trend = go.Figure()
    
    # Dados históricos
    if len(recent_data) > 0:
        fig_trend.add_trace(go.Scatter(
            x=recent_data['periodo'],
            y=recent_data['total_vouchers'],
            mode='lines+markers',
            name='Histórico',
            line=dict(color='#3498db', width=3),
            marker=dict(size=8)
        ))
    
    # Projeção do mês atual
    if projected_vouchers > 0:
        current_month_start = pd.Timestamp(current_year, current_month, 1)
        fig_trend.add_trace(go.Scatter(
            x=[current_month_start],
            y=[projected_vouchers],
            mode='markers',
            name='Projeção Atual',
            marker=dict(color='#e74c3c', size=12, symbol='diamond')
        ))
    
    fig_trend.update_layout(
        title="📈 Tendência e Projeção Mensal de Vouchers",
        xaxis_title="Período",
        yaxis_title="Quantidade de Vouchers",
        height=400,
        showlegend=True
    )
    
    # Análise por rede - Top performers do mês atual
    if len(current_month_data) > 0:
        current_networks = current_month_data.groupby('nome_rede').agg({
            'imei': 'count',
            'valor_dispositivo': 'sum'
        }).round(2)
        current_networks.columns = ['Vouchers_Atual', 'Valor_Atual']
        current_networks = current_networks.sort_values('Vouchers_Atual', ascending=False).head(10)
    else:
        current_networks = pd.DataFrame(columns=['Vouchers_Atual', 'Valor_Atual'])
    
    # Gráfico de performance atual por rede
    if len(current_networks) > 0:
        fig_networks = px.bar(
            x=current_networks.index,
            y=current_networks['Vouchers_Atual'],
            title=f"🏆 Top 10 Redes - Performance {pd.Timestamp(current_year, current_month, 1).strftime('%B %Y')}",
            labels={'x': 'Rede', 'y': 'Vouchers no Mês'},
            color=current_networks['Vouchers_Atual'],
            color_continuous_scale='viridis'
        )
        fig_networks.update_layout(height=400, xaxis_tickangle=-45)
    else:
        fig_networks = go.Figure()
        fig_networks.add_annotation(
            text="Dados insuficientes para análise por rede",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font_size=16
        )
        fig_networks.update_layout(height=400, title="Performance por Rede")
    
    # Meta estimada baseada na média histórica
    if len(recent_data) >= 3:
        historical_avg = recent_data['total_vouchers'].mean()
        meta_performance = (projected_vouchers / historical_avg * 100) if historical_avg > 0 else 100
    else:
        historical_avg = 0
        meta_performance = 100
    
    # Indicador de meta
    meta_card = dbc.Card([
        dbc.CardHeader(html.H5("🎯 Análise de Meta", className="mb-0 text-center")),
        dbc.CardBody([
            html.Div([
                html.H3(f"{meta_performance:.0f}%", 
                       className=f"text-{'success' if meta_performance >= 100 else 'warning'} text-center mb-2"),
                html.P(f"Performance vs média histórica ({historical_avg:.0f} vouchers/mês)" if len(recent_data) >= 3 else "Dados insuficientes para meta histórica", 
                      className="text-center text-muted mb-0")
            ])
        ])
    ], className="mb-4")
    
    return html.Div([
        html.H4("🔮 Projeções e Análise do Mês Atual", className="mb-4"),
        projection_cards,
        meta_card,
        dbc.Row([
            dbc.Col([dcc.Graph(figure=fig_trend)], md=8),
            dbc.Col([dcc.Graph(figure=fig_networks)], md=4)
        ]),
        html.Hr(),
        html.H5("📊 Insights e Recomendações", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.H6("💡 Análise de Tendência", className="mb-2"),
                    html.P(f"Baseado nos dados atuais, a projeção indica {'crescimento' if growth_vouchers > 0 else 'queda'} de {abs(growth_vouchers):.1f}% em relação ao mês anterior.", className="mb-1"),
                    html.P(f"Para atingir a meta histórica, seria necessário {'manter o ritmo atual' if meta_performance >= 100 else f'aumentar a performance em {100-meta_performance:.0f}%'}.", className="mb-0")
                ], color="info")
            ], md=6),
            dbc.Col([
                dbc.Alert([
                    html.H6("🎯 Recomendações", className="mb-2"),
                    html.P("• Foque nas redes com melhor performance atual" if len(current_networks) > 0 else "• Aguarde mais dados para análise", className="mb-1"),
                    html.P(f"• Intensifique ações nos {'últimos' if days_passed > days_in_month//2 else 'próximos'} {days_in_month-days_passed} dias do mês", className="mb-1"),
                    html.P(f"• Meta diária recomendada: {(projected_vouchers-current_vouchers)/(days_in_month-days_passed):.0f} vouchers/dia" if days_in_month > days_passed and projected_vouchers > current_vouchers else "• Meta mensal em finalização", className="mb-0")
                ], color="success")
            ], md=6)
        ])
    ])

# ========================
# 🔚 Execução
# ========================
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 8080)), host='0.0.0.0')