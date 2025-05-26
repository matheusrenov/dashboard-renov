import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from unidecode import unidecode

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
            html.H1("📊 Dashboard de Resultados", className="text-center mb-4", 
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
            html.H4("Bem-vindo ao Dashboard de Resultados!"),
            html.P("Carregue uma planilha Excel (.xlsx) para começar a análise dos dados.")
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
            dcc.Tab(label="🏆 Rankings", value="rankings")
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
        df.columns = [unidecode(str(col)).strip().lower().replace(' ', '_') for col in df.columns]
        
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
    
    def create_kpi_card(title, value, color="primary"):
        return dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(title, className="card-title text-muted mb-2"),
                    html.H3(value, className=f"text-{color} fw-bold mb-0")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=2)
    
    return dbc.Row([
        create_kpi_card("Vouchers Totais", f"{total_vouchers:,}", "info"),
        create_kpi_card("Vouchers Utilizados", f"{total_used:,}", "success"),
        create_kpi_card("Valor Total", f"R$ {total_value:,.2f}", "warning"),
        create_kpi_card("Ticket Médio", f"R$ {avg_ticket:,.2f}", "primary"),
        create_kpi_card("Taxa Conversão", f"{conversion_rate:.1f}%", "danger")
    ], className="g-3 mb-4")

def generate_overview_content(df):
    # Gráfico de pizza - distribuição por situação
    status_counts = df['situacao_voucher'].value_counts()
    fig_pie = px.pie(
        values=status_counts.values, 
        names=status_counts.index,
        title="📊 Distribuição por Situação"
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    
    # Gráfico de barras - top redes
    network_counts = df['nome_rede'].value_counts().head(8)
    fig_bar = px.bar(
        x=network_counts.values,
        y=network_counts.index,
        orientation='h',
        title="🏪 Volume por Rede",
        labels={'x': 'Quantidade', 'y': 'Rede'}
    )
    fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'})
    
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
        title="📅 Vouchers por Dia"
    )
    fig_line.update_traces(line_color='#3498db', line_width=2)
    
    # Distribuição por mês
    monthly_counts = df.groupby(['mes', 'ano']).size().reset_index(name='count')
    monthly_counts['periodo'] = monthly_counts['mes'] + '/' + monthly_counts['ano'].astype(str)
    
    fig_monthly = px.bar(
        monthly_counts,
        x='periodo',
        y='count',
        title="📊 Vouchers por Mês"
    )
    
    return dbc.Row([
        dbc.Col([dcc.Graph(figure=fig_line)], md=12),
        dbc.Col([dcc.Graph(figure=fig_monthly)], md=12)
    ])

def generate_networks_content(df):
    # Análise por rede
    network_analysis = df.groupby('nome_rede').agg({
        'imei': 'count',
        'valor_dispositivo': 'sum',
        'valor_voucher': 'mean'
    }).round(2)
    network_analysis.columns = ['Total_Vouchers', 'Valor_Total', 'Ticket_Medio']
    network_analysis = network_analysis.reset_index().sort_values('Total_Vouchers', ascending=False)
    
    # Gráfico scatter
    fig_scatter = px.scatter(
        network_analysis,
        x='Total_Vouchers',
        y='Valor_Total',
        size='Ticket_Medio',
        hover_name='nome_rede',
        title="💰 Performance das Redes: Volume vs Valor"
    )
    
    return dbc.Row([
        dbc.Col([dcc.Graph(figure=fig_scatter)], md=12),
        dbc.Col([
            html.H5("📋 Detalhamento por Rede"),
            dash_table.DataTable(
                data=network_analysis.to_dict('records'),
                columns=[
                    {"name": "Rede", "id": "nome_rede"},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric"},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.2f"}},
                    {"name": "Ticket Médio", "id": "Ticket_Medio", "type": "numeric", "format": {"specifier": ",.2f"}}
                ],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
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
    seller_stats = seller_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(15)
    
    return dbc.Row([
        dbc.Col([
            html.H5("🏆 Top 15 Vendedores"),
            dash_table.DataTable(
                data=seller_stats.to_dict('records'),
                columns=[
                    {"name": "Vendedor", "id": "nome_vendedor"},
                    {"name": "Filial", "id": "nome_filial"},
                    {"name": "Rede", "id": "nome_rede"},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric"},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.2f"}}
                ],
                style_cell={'textAlign': 'left', 'fontSize': '12px'},
                style_header={'backgroundColor': '#28a745', 'color': 'white', 'fontWeight': 'bold'},
                page_size=15,
                sort_action="native"
            )
        ], md=12)
    ])

# ========================
# 🔚 Execução
# ========================
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 8080)), host='0.0.0.0')