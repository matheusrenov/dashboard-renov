import os
import base64
import io
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context, ALL
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

# Configuração para evitar que os componentes sejam destruídos ao trocar de aba
app.config.suppress_callback_exceptions = True

# ========================
# 🎨 Layout Principal
# ========================
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("📊 Dashboard de Performance Renov", 
                   className="text-center mb-4", 
                   style={'color': '#2c3e50', 'fontWeight': 'bold'}),
            html.Hr(style={'borderColor': '#3498db', 'borderWidth': '2px'})
        ])
    ]),

    # Controles de upload
    dbc.Row([
        dbc.Col([
            dcc.Upload(
                id="upload-vouchers",
                children=dbc.Button([
                    html.I(className="fas fa-upload me-2"),
                    "📁 Importar Base de Vouchers"
                ], color="primary", size="lg", className="w-100"),
                accept=".xlsx,.xls",
                multiple=False
            )
        ], md=4),
        dbc.Col([
            dcc.Upload(
                id="upload-lojas",
                children=dbc.Button([
                    html.I(className="fas fa-store me-2"),
                    "🏪 Importar Base de Lojas"
                ], color="info", size="lg", className="w-100"),
                accept=".xlsx,.xls",
                multiple=False
            )
        ], md=4),
        dbc.Col([
            dcc.Upload(
                id="upload-colaboradores",
                children=dbc.Button([
                    html.I(className="fas fa-users me-2"),
                    "👥 Importar Base Colaboradores"
                ], color="success", size="lg", className="w-100"),
                accept=".xlsx,.xls",
                multiple=False
            )
        ], md=4)
    ], className="mb-4"),

    # Container para alertas
    html.Div(id='alerts-container'),

    # Stores para dados
    dcc.Store(id='store-vouchers'),
    dcc.Store(id='store-lojas'),
    dcc.Store(id='store-colaboradores'),
    dcc.Store(id='store-filtered-data'),

    # Status dos uploads
    dbc.Row([
        dbc.Col([
            html.Div(id='upload-status', className="mb-3")
        ])
    ]),

    # Estado inicial - aguardando upload
    html.Div(id='welcome-message', children=[
        dbc.Alert([
            html.I(className="fas fa-cloud-upload-alt fa-3x mb-3"),
            html.H4("Bem-vindo ao Dashboard de Performance Renov!"),
            html.P("Carregue as planilhas Excel para começar a análise estratégica:"),
            html.Ul([
                html.Li("📁 Base de Vouchers - Dados principais das transações"),
                html.Li("🏪 Base de Lojas - Informações das lojas parceiras"),
                html.Li("👥 Base de Colaboradores - Dados dos vendedores")
            ])
        ], color="info", className="text-center py-5")
    ]),

    # Filtros
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
    
    # KPIs
    html.Div(id='kpi-section'),
    
    # Abas
    html.Div(id='tabs-section', style={'display': 'none'}, children=[
        dcc.Tabs(id="main-tabs", value="overview", children=[
            dcc.Tab(label="📈 Visão Geral", value="overview"),
            dcc.Tab(label="🏪 Análise por Redes", value="networks"),
            dcc.Tab(label="🏆 Rankings", value="rankings"),
            dcc.Tab(label="📊 Base de Lojas", value="lojas"),
            dcc.Tab(label="👥 Base de Colaboradores", value="colaboradores"),
            dcc.Tab(label="🔮 Projeções", value="projections")
        ], className="mb-3")
    ]),
    
    # Conteúdo das abas
    html.Div(id='tab-content-area')

], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'padding': '20px'})

# ========================
# 📥 CALLBACK DE UPLOAD DE VOUCHERS
# ========================
@app.callback(
    [Output('store-vouchers', 'data'),
     Output('alerts-container', 'children', allow_duplicate=True)],
    [Input('upload-vouchers', 'contents')],
    [State('upload-vouchers', 'filename'),
     State('alerts-container', 'children')],
    prevent_initial_call=True
)
def handle_vouchers_upload(contents, filename, current_alerts):
    if not contents:
        return {}, current_alerts or []
    
    alerts = current_alerts or []
    
    try:
        # Decodificar arquivo
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        
        if df.empty:
            alerts.append(dbc.Alert("❌ Arquivo de vouchers vazio!", color="danger", dismissable=True))
            return {}, alerts
        
        # Normalizar colunas
        df.columns = [unidecode(str(col)).strip().lower().replace(' ', '_') for col in df.columns]
        
        # Processar datas
        if 'criado_em' in df.columns:
            df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
            df = df.dropna(subset=['criado_em'])
            df['mes'] = df['criado_em'].dt.strftime('%b')
            df['ano'] = df['criado_em'].dt.year
            df['data_str'] = df['criado_em'].dt.strftime('%Y-%m-%d')
        
        # Processar valores
        for col in ['valor_voucher', 'valor_do_voucher', 'valor_dispositivo', 'valor_do_dispositivo']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        alerts.append(dbc.Alert(f"✅ Base de Vouchers carregada: {len(df)} registros", color="success", dismissable=True))
        return df.to_dict('records'), alerts
        
    except Exception as e:
        alerts.append(dbc.Alert(f"❌ Erro ao processar vouchers: {str(e)}", color="danger", dismissable=True))
        return {}, alerts

# ========================
# 📥 CALLBACK DE UPLOAD DE LOJAS
# ========================
@app.callback(
    [Output('store-lojas', 'data'),
     Output('alerts-container', 'children', allow_duplicate=True)],
    [Input('upload-lojas', 'contents')],
    [State('upload-lojas', 'filename'),
     State('alerts-container', 'children')],
    prevent_initial_call=True
)
def handle_lojas_upload(contents, filename, current_alerts):
    if not contents:
        return {}, current_alerts or []
    
    alerts = current_alerts or []
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        
        if df.empty:
            alerts.append(dbc.Alert("❌ Arquivo de lojas vazio!", color="danger", dismissable=True))
            return {}, alerts
        
        # Normalizar colunas
        df.columns = [unidecode(str(col)).strip().lower().replace(' ', '_') for col in df.columns]
        
        alerts.append(dbc.Alert(f"✅ Base de Lojas carregada: {len(df)} registros", color="success", dismissable=True))
        return df.to_dict('records'), alerts
        
    except Exception as e:
        alerts.append(dbc.Alert(f"❌ Erro ao processar lojas: {str(e)}", color="danger", dismissable=True))
        return {}, alerts

# ========================
# 📥 CALLBACK DE UPLOAD DE COLABORADORES
# ========================
@app.callback(
    [Output('store-colaboradores', 'data'),
     Output('alerts-container', 'children', allow_duplicate=True)],
    [Input('upload-colaboradores', 'contents')],
    [State('upload-colaboradores', 'filename'),
     State('alerts-container', 'children')],
    prevent_initial_call=True
)
def handle_colaboradores_upload(contents, filename, current_alerts):
    if not contents:
        return {}, current_alerts or []
    
    alerts = current_alerts or []
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        
        if df.empty:
            alerts.append(dbc.Alert("❌ Arquivo de colaboradores vazio!", color="danger", dismissable=True))
            return {}, alerts
        
        # Normalizar colunas
        df.columns = [unidecode(str(col)).strip().lower().replace(' ', '_') for col in df.columns]
        
        alerts.append(dbc.Alert(f"✅ Base de Colaboradores carregada: {len(df)} registros", color="success", dismissable=True))
        return df.to_dict('records'), alerts
        
    except Exception as e:
        alerts.append(dbc.Alert(f"❌ Erro ao processar colaboradores: {str(e)}", color="danger", dismissable=True))
        return {}, alerts

# ========================
# 🔄 CALLBACK PARA ATUALIZAR INTERFACE
# ========================
@app.callback(
    [Output('welcome-message', 'style'),
     Output('filters-section', 'style'),
     Output('tabs-section', 'style'),
     Output('filter-month', 'options'),
     Output('filter-network', 'options'),
     Output('filter-status', 'options'),
     Output('upload-status', 'children')],
    [Input('store-vouchers', 'data'),
     Input('store-lojas', 'data'),
     Input('store-colaboradores', 'data')],
    prevent_initial_call=True
)
def update_interface(vouchers_data, lojas_data, colaboradores_data):
    # Status dos uploads
    status_badges = []
    if vouchers_data:
        status_badges.append(dbc.Badge("✅ Vouchers", color="success", className="me-2"))
    if lojas_data:
        status_badges.append(dbc.Badge("✅ Lojas", color="success", className="me-2"))
    if colaboradores_data:
        status_badges.append(dbc.Badge("✅ Colaboradores", color="success", className="me-2"))
    
    # Se nenhum dado foi carregado
    if not vouchers_data:
        return {'display': 'block'}, {'display': 'none'}, {'display': 'none'}, [], [], [], status_badges
    
    # Processar dados para filtros
    df = pd.DataFrame(vouchers_data)
    
    month_options = []
    if 'mes' in df.columns and 'ano' in df.columns:
        month_options = [
            {'label': f"{month} ({year})", 'value': f"{month}_{year}"} 
            for month, year in df.groupby(['mes', 'ano']).size().index
        ]
    
    network_options = []
    if 'nome_da_rede' in df.columns:
        network_options = [
            {'label': network, 'value': network} 
            for network in sorted(df['nome_da_rede'].dropna().unique())
        ]
    
    status_options = []
    if 'situacao_do_voucher' in df.columns:
        status_options = [
            {'label': status, 'value': status} 
            for status in sorted(df['situacao_do_voucher'].dropna().unique())
        ]
    
    return {'display': 'none'}, {'display': 'block'}, {'display': 'block'}, month_options, network_options, status_options, status_badges

# ========================
# 🔄 CALLBACK PARA APLICAR FILTROS
# ========================
@app.callback(
    Output('store-filtered-data', 'data'),
    [Input('filter-month', 'value'),
     Input('filter-network', 'value'),
     Input('filter-status', 'value'),
     Input('clear-filters', 'n_clicks')],
    [State('store-vouchers', 'data')],
    prevent_initial_call=True
)
def apply_filters(months, networks, statuses, clear_clicks, vouchers_data):
    if not vouchers_data:
        return {}
    
    ctx = callback_context
    if ctx.triggered and 'clear-filters' in ctx.triggered[0]['prop_id']:
        return vouchers_data
    
    df = pd.DataFrame(vouchers_data)
    
    # Aplicar filtros respeitando as variações de nomes de colunas
    if months and ('mes' in df.columns and 'ano' in df.columns):
        month_year_filters = [f"{row['mes']}_{row['ano']}" for _, row in df.iterrows()]
        df = df[[mf in months for mf in month_year_filters]]
    
    if networks:
        rede_col = 'nome_da_rede' if 'nome_da_rede' in df.columns else 'nome_rede'
        if rede_col in df.columns:
            df = df[df[rede_col].isin(networks)]
    
    if statuses:
        status_col = 'situacao_do_voucher' if 'situacao_do_voucher' in df.columns else 'situacao_voucher'
        if status_col in df.columns:
            df = df[df[status_col].isin(statuses)]
    
    return df.to_dict('records')

# ========================
# 📊 CALLBACK PARA KPIs
# ========================
@app.callback(
    Output('kpi-section', 'children'),
    [Input('store-vouchers', 'data'),
     Input('store-filtered-data', 'data'),
     Input('store-lojas', 'data')],
    prevent_initial_call=True
)
def update_kpis(vouchers_data, filtered_data, lojas_data):
    data_to_use = filtered_data if filtered_data else vouchers_data
    if not data_to_use:
        return html.Div()
    
    df = pd.DataFrame(data_to_use)
    df_lojas = pd.DataFrame(lojas_data) if lojas_data else pd.DataFrame()
    
    # Calcular KPIs
    total_vouchers = len(df)
    
    # Identificar vouchers utilizados
    used_mask = df['situacao_do_voucher'].str.upper().str.contains('UTILIZADO', na=False) if 'situacao_do_voucher' in df.columns else pd.Series([False] * len(df))
    used_vouchers = df[used_mask]
    total_used = len(used_vouchers)
    
    # Valores
    valor_col = 'valor_do_dispositivo' if 'valor_do_dispositivo' in df.columns else 'valor_dispositivo'
    total_value = used_vouchers[valor_col].sum() if valor_col in used_vouchers.columns else 0
    avg_ticket = total_value / total_used if total_used > 0 else 0
    conversion_rate = (total_used / total_vouchers * 100) if total_vouchers > 0 else 0
    
    # Lojas
    filial_col = 'nome_da_filial' if 'nome_da_filial' in df.columns else 'nome_filial'
    total_stores = df[filial_col].nunique() if filial_col in df.columns else 0
    active_stores = used_vouchers[filial_col].nunique() if filial_col in used_vouchers.columns else 0
    
    # KPIs da base de lojas
    total_lojas_base = 0
    total_redes_ativas = 0
    lojas_com_geracao_pct = 0
    
    if not df_lojas.empty:
        # Total de lojas na base
        total_lojas_base = len(df_lojas)
        
        # Redes ativas
        status_col = None
        rede_col = None
        for col in df_lojas.columns:
            if 'status' in col.lower() or 'situacao' in col.lower():
                status_col = col
            if 'rede' in col.lower() and 'nome' in col.lower():
                rede_col = col
        
        if status_col and rede_col:
            df_ativas = df_lojas[df_lojas[status_col].str.lower() == 'ativa']
            # Filtrar Renov dos resultados
            df_ativas = df_ativas[df_ativas[rede_col].str.upper() != 'RENOV']
            total_redes_ativas = df_ativas[rede_col].nunique()
        
        # Percentual de lojas com geração
        if total_lojas_base > 0:
            lojas_com_geracao_pct = (total_stores / total_lojas_base * 100)
    
    # Primeira linha de KPIs
    primeira_linha = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Vouchers Totais", className="card-title text-muted mb-2"),
                    html.H3(f"{total_vouchers:,}", className="text-info fw-bold mb-1")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Vouchers Utilizados", className="card-title text-muted mb-2"),
                    html.H3(f"{total_used:,}", className="text-success fw-bold mb-1"),
                    html.Small(f"{conversion_rate:.1f}% conversão", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Valor Total", className="card-title text-muted mb-2"),
                    html.H3(f"R$ {total_value:,.0f}", className="text-warning fw-bold mb-1")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Ticket Médio", className="card-title text-muted mb-2"),
                    html.H3(f"R$ {avg_ticket:,.0f}", className="text-primary fw-bold mb-1")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=3)
    ], className="g-2 mb-3")
    
    # Segunda linha de KPIs
    segunda_linha = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total Redes Ativas", className="card-title text-muted mb-2"),
                    html.H3(f"{total_redes_ativas}", className="text-success fw-bold mb-1")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total de Lojas", className="card-title text-muted mb-2"),
                    html.H3(f"{total_lojas_base:,}", className="text-info fw-bold mb-1")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Lojas Totais", className="card-title text-muted mb-2"),
                    html.H3(f"{total_stores}", className="text-danger fw-bold mb-1"),
                    html.Small(f"{lojas_com_geracao_pct:.1f}% com voucher", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Lojas Ativas", className="card-title text-muted mb-2"),
                    html.H3(f"{active_stores}", className="text-dark fw-bold mb-1"),
                    html.Small(f"{(active_stores/total_stores*100):.1f}% do total" if total_stores > 0 else "0%", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], md=3)
    ], className="g-2 mb-4")
    
    return html.Div([primeira_linha, segunda_linha])

# ========================
# 📈 CALLBACK PARA CONTEÚDO DAS ABAS
# ========================
@app.callback(
    Output('tab-content-area', 'children'),
    [Input('main-tabs', 'value'),
     Input('store-filtered-data', 'data'),
     Input('store-vouchers', 'data'),
     Input('store-lojas', 'data'),
     Input('store-colaboradores', 'data')],
    prevent_initial_call=True
)
def update_tab_content(active_tab, filtered_data, vouchers_data, lojas_data, colaboradores_data):
    try:
        data_to_use = filtered_data if filtered_data else vouchers_data
        
        if active_tab == "overview":
            if not data_to_use:
                return dbc.Alert("Carregue a base de vouchers para visualizar a visão geral.", color="warning")
            return generate_overview_content(pd.DataFrame(data_to_use))
            
        elif active_tab == "networks":
            if not data_to_use:
                return dbc.Alert("Carregue a base de vouchers para visualizar análise por redes.", color="warning")
            return generate_networks_content(pd.DataFrame(data_to_use))
            
        elif active_tab == "rankings":
            if not data_to_use:
                return dbc.Alert("Carregue a base de vouchers para visualizar rankings.", color="warning")
            return generate_rankings_content(pd.DataFrame(data_to_use))
            
        elif active_tab == "lojas":
            if not lojas_data:
                return dbc.Alert("Carregue a base de lojas para visualizar os dados.", color="warning")
            # Passar também os dados de vouchers para calcular lojas sem geração
            return generate_lojas_content(pd.DataFrame(lojas_data), pd.DataFrame(data_to_use) if data_to_use else None)
            
        elif active_tab == "colaboradores":
            if not colaboradores_data:
                return dbc.Alert("Carregue a base de colaboradores para visualizar os dados.", color="warning")
            return generate_colaboradores_content(pd.DataFrame(colaboradores_data))
            
        elif active_tab == "projections":
            if not vouchers_data:
                return dbc.Alert("Carregue a base de vouchers para visualizar projeções.", color="warning")
            return generate_projections_content(pd.DataFrame(vouchers_data), pd.DataFrame(data_to_use))
            
        else:
            return html.Div("Aba não encontrada")
            
    except Exception as e:
        return dbc.Alert(f"Erro ao processar dados: {str(e)}", color="danger")

# ========================
# 📊 FUNÇÕES DE GERAÇÃO DE CONTEÚDO
# ========================
def generate_overview_content(df):
    try:
        # Preparar colunas
        situacao_col = 'situacao_do_voucher' if 'situacao_do_voucher' in df.columns else 'situacao_voucher'
        rede_col = 'nome_da_rede' if 'nome_da_rede' in df.columns else 'nome_rede'
        valor_col = 'valor_do_dispositivo' if 'valor_do_dispositivo' in df.columns else 'valor_dispositivo'
        
        # Gráfico de pizza - distribuição por situação
        if situacao_col in df.columns:
            status_counts = df[situacao_col].value_counts()
            fig_pie = px.pie(
                values=status_counts.values, 
                names=status_counts.index,
                title="📊 Distribuição por Situação"
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(height=400)
        else:
            fig_pie = go.Figure()
            fig_pie.add_annotation(text="Dados de situação não disponíveis", x=0.5, y=0.5, showarrow=False)
            fig_pie.update_layout(height=400)
        
        # Gráfico de barras - top redes
        if rede_col in df.columns:
            # Filtrar Renov
            df_sem_renov = df[df[rede_col].str.upper() != 'RENOV']
            
            # Total de vouchers (AGORA PRIMEIRO)
            network_counts = df_sem_renov[rede_col].value_counts().head(10)
            fig_bar_total = go.Figure()
            fig_bar_total.add_trace(go.Bar(
                x=network_counts.values,
                y=network_counts.index,
                orientation='h',
                text=network_counts.values,
                textposition='outside',
                marker_color='lightblue'
            ))
            fig_bar_total.update_layout(
                title="🏪 Volume Total por Rede (Top 10)",
                yaxis={'categoryorder': 'total ascending'},
                height=400,
                xaxis_title="Quantidade",
                yaxis_title="Rede"
            )
            
            # Vouchers utilizados (AGORA SEGUNDO)
            if situacao_col in df_sem_renov.columns:
                used_mask = df_sem_renov[situacao_col].str.upper().str.contains('UTILIZADO', na=False)
                used_vouchers = df_sem_renov[used_mask]
                if not used_vouchers.empty:
                    network_used_counts = used_vouchers[rede_col].value_counts().head(10)
                    fig_bar_used = go.Figure()
                    fig_bar_used.add_trace(go.Bar(
                        x=network_used_counts.values,
                        y=network_used_counts.index,
                        orientation='h',
                        text=network_used_counts.values,
                        textposition='outside',
                        marker_color='lightgreen'
                    ))
                    fig_bar_used.update_layout(
                        title="✅ Vouchers Utilizados por Rede (Top 10)",
                        yaxis={'categoryorder': 'total ascending'},
                        height=400,
                        xaxis_title="Quantidade",
                        yaxis_title="Rede"
                    )
                else:
                    fig_bar_used = go.Figure()
                    fig_bar_used.add_annotation(text="Nenhum voucher utilizado", x=0.5, y=0.5, showarrow=False)
                    fig_bar_used.update_layout(height=400)
            else:
                fig_bar_used = fig_bar_total
        else:
            fig_bar_total = go.Figure()
            fig_bar_total.add_annotation(text="Dados de rede não disponíveis", x=0.5, y=0.5, showarrow=False)
            fig_bar_total.update_layout(height=400)
            fig_bar_used = fig_bar_total
        
        # Evolução temporal
        if 'data_str' in df.columns:
            daily_series = df.groupby('data_str').size().reset_index(name='count')
            daily_series['data_str'] = pd.to_datetime(daily_series['data_str'])
            
            # Obter mês atual
            if not daily_series.empty:
                mes_atual = daily_series['data_str'].max().month
                ano_atual = daily_series['data_str'].max().year
                
                # Criar série completa do mês
                primeiro_dia = pd.Timestamp(ano_atual, mes_atual, 1)
                ultimo_dia = pd.Timestamp(ano_atual, mes_atual, pd.Timestamp(ano_atual, mes_atual, 1).days_in_month)
                datas_completas = pd.date_range(start=primeiro_dia, end=ultimo_dia, freq='D')
                
                # Merge com dados existentes
                df_completo = pd.DataFrame({'data_str': datas_completas})
                df_completo = df_completo.merge(daily_series, on='data_str', how='left')
                df_completo['count'] = df_completo['count'].fillna(0)
                df_completo['dia'] = df_completo['data_str'].dt.day
                
                fig_line = px.line(
                    df_completo, 
                    x='dia', 
                    y='count',
                    title="📅 Evolução Diária de Vouchers",
                    labels={'dia': 'Dia', 'count': 'Quantidade'}
                )
                fig_line.update_traces(line_color='#3498db', line_width=3)
                fig_line.update_layout(
                    height=350,
                    xaxis=dict(
                        tickmode='linear',
                        tick0=1,
                        dtick=1,
                        showgrid=False
                    ),
                    yaxis=dict(showgrid=False),
                    plot_bgcolor='white'
                )
            else:
                fig_line = go.Figure()
                fig_line.add_annotation(text="Dados temporais não disponíveis", x=0.5, y=0.5, showarrow=False)
                fig_line.update_layout(height=350)
        else:
            fig_line = go.Figure()
            fig_line.add_annotation(text="Dados temporais não disponíveis", x=0.5, y=0.5, showarrow=False)
            fig_line.update_layout(height=350)
        
        # Análise por rede para tabela
        unique_days = df['data_str'].nunique() if 'data_str' in df.columns else 1
        
        network_summary = []
        if rede_col in df.columns:
            # Filtrar Renov
            df_analysis = df[df[rede_col].str.upper() != 'RENOV']
            
            for rede in df_analysis[rede_col].unique():
                rede_data = df_analysis[df_analysis[rede_col] == rede]
                
                if situacao_col in rede_data.columns:
                    rede_used = rede_data[rede_data[situacao_col].str.upper().str.contains('UTILIZADO', na=False)]
                else:
                    rede_used = pd.DataFrame()
                
                vouchers_totais = len(rede_data)
                vouchers_utilizados = len(rede_used)
                valor_total = rede_used[valor_col].sum() if valor_col in rede_used.columns and len(rede_used) > 0 else 0
                ticket_medio = valor_total / vouchers_utilizados if vouchers_utilizados > 0 else 0
                
                filial_col = 'nome_da_filial' if 'nome_da_filial' in df.columns else 'nome_filial'
                lojas_totais = rede_data[filial_col].nunique() if filial_col in rede_data.columns else 0
                lojas_ativas = rede_used[filial_col].nunique() if filial_col in rede_used.columns and len(rede_used) > 0 else 0
                
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
        network_summary = sorted(network_summary, key=lambda x: x['Vouchers_Utilizados'], reverse=True)
        
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
            # Primeira linha: Gráficos de volume (ORDEM INVERTIDA)
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_bar_total)], md=6),
                dbc.Col([dcc.Graph(figure=fig_bar_used)], md=6)
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
            fig_bar_total = go.Figure()
            fig_bar_total.add_annotation(text="Dados de rede não disponíveis", x=0.5, y=0.5, showarrow=False)
            fig_bar_total.update_layout(height=400)
            fig_bar_used = fig_bar_total
        
        # Evolução temporal
        if 'data_str' in df.columns:
            daily_series = df.groupby('data_str').size().reset_index(name='count')
            daily_series['data_str'] = pd.to_datetime(daily_series['data_str'])
            
            fig_line = px.line(
                daily_series, 
                x='data_str', 
                y='count',
                title="📅 Evolução Diária de Vouchers",
                labels={'data_str': 'Data', 'count': 'Quantidade'}
            )
            fig_line.update_traces(line_color='#3498db', line_width=3)
            fig_line.update_layout(height=350)
        else:
            fig_line = go.Figure()
            fig_line.add_annotation(text="Dados temporais não disponíveis", x=0.5, y=0.5, showarrow=False)
            fig_line.update_layout(height=350)
        
        return html.Div([
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_bar_used)], md=6),
                dbc.Col([dcc.Graph(figure=fig_bar_total)], md=6)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_pie)], md=6),
                dbc.Col([dcc.Graph(figure=fig_line)], md=6)
            ], className="mb-4")
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro na visão geral: {str(e)}", color="danger")

def generate_networks_content(df):
    try:
        rede_col = 'nome_da_rede' if 'nome_da_rede' in df.columns else 'nome_rede'
        valor_col = 'valor_do_dispositivo' if 'valor_do_dispositivo' in df.columns else 'valor_dispositivo'
        filial_col = 'nome_da_filial' if 'nome_da_filial' in df.columns else 'nome_filial'
        
        if rede_col not in df.columns:
            return dbc.Alert("Dados de redes não disponíveis.", color="warning")
        
        # Filtrar Renov
        df = df[df[rede_col].str.upper() != 'RENOV']
        
        # Análise por rede
        network_analysis = df.groupby(rede_col).agg({
            'imei': 'count',
            valor_col: 'sum' if valor_col in df.columns else lambda x: 0,
            filial_col: 'nunique' if filial_col in df.columns else lambda x: 0
        }).round(2)
        network_analysis.columns = ['Total_Vouchers', 'Valor_Total', 'Num_Lojas']
        network_analysis = network_analysis.reset_index()
        network_analysis['Ticket_Medio'] = network_analysis['Valor_Total'] / network_analysis['Total_Vouchers']
        
        # Gráfico scatter
        fig_scatter = px.scatter(
            network_analysis,
            x='Total_Vouchers',
            y='Valor_Total',
            size='Num_Lojas',
            hover_name=rede_col,
            title="💰 Performance das Redes: Volume vs Valor",
            labels={'Total_Vouchers': 'Total de Vouchers', 'Valor_Total': 'Valor Total (R$)'}
        )
        fig_scatter.update_layout(height=500)
        
        # Tabela detalhada
        network_table = dash_table.DataTable(
            data=network_analysis.to_dict('records'),
            columns=[
                {"name": "Rede", "id": rede_col},
                {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric"},
                {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.0f"}},
                {"name": "Número de Lojas", "id": "Num_Lojas", "type": "numeric"},
                {"name": "Ticket Médio", "id": "Ticket_Medio", "type": "numeric", "format": {"specifier": ",.2f"}}
            ],
            style_cell={'textAlign': 'left'},
            style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
            sort_action="native",
            page_size=15
        )
        
        return html.Div([
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_scatter)], md=12)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    html.H5("📋 Detalhamento por Rede", className="mb-3"),
                    network_table
                ], md=12)
            ])
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro na análise de redes: {str(e)}", color="danger")

def generate_rankings_content(df):
    try:
        vendedor_col = 'nome_do_vendedor' if 'nome_do_vendedor' in df.columns else 'nome_vendedor'
        filial_col = 'nome_da_filial' if 'nome_da_filial' in df.columns else 'nome_filial'
        rede_col = 'nome_da_rede' if 'nome_da_rede' in df.columns else 'nome_rede'
        valor_col = 'valor_do_dispositivo' if 'valor_do_dispositivo' in df.columns else 'valor_dispositivo'
        
        # Filtrar Renov
        if rede_col in df.columns:
            df = df[df[rede_col].str.upper() != 'RENOV']
        
        # Ranking de lojas
        if filial_col in df.columns:
            store_stats = df.groupby([filial_col, rede_col] if rede_col in df.columns else [filial_col]).agg({
                'imei': 'count',
                valor_col: 'sum' if valor_col in df.columns else lambda x: 0
            }).round(2)
            store_stats.columns = ['Total_Vouchers', 'Valor_Total']
            store_stats = store_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(25)
            
            store_table = dash_table.DataTable(
                data=store_stats.to_dict('records'),
                columns=[
                    {"name": "Loja", "id": filial_col},
                    {"name": "Rede", "id": rede_col} if rede_col in df.columns else {"name": "Loja", "id": filial_col},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric"},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.0f"}}
                ],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': '#e74c3c', 'color': 'white', 'fontWeight': 'bold'},
                page_size=25,
                sort_action="native"
            )
        else:
            store_table = html.P("Dados de lojas não disponíveis")
        
        # Ranking de vendedores
        if vendedor_col in df.columns:
            seller_stats = df.groupby([vendedor_col, filial_col] if filial_col in df.columns else [vendedor_col]).agg({
                'imei': 'count',
                valor_col: 'sum' if valor_col in df.columns else lambda x: 0
            }).round(2)
            seller_stats.columns = ['Total_Vouchers', 'Valor_Total']
            seller_stats = seller_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(25)
            
            seller_table = dash_table.DataTable(
                data=seller_stats.to_dict('records'),
                columns=[
                    {"name": "Vendedor", "id": vendedor_col},
                    {"name": "Loja", "id": filial_col} if filial_col in df.columns else {"name": "Vendedor", "id": vendedor_col},
                    {"name": "Total Vouchers", "id": "Total_Vouchers", "type": "numeric"},
                    {"name": "Valor Total", "id": "Valor_Total", "type": "numeric", "format": {"specifier": ",.0f"}}
                ],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': '#27ae60', 'color': 'white', 'fontWeight': 'bold'},
                page_size=25,
                sort_action="native"
            )
        else:
            seller_table = html.P("Dados de vendedores não disponíveis")
        
        return html.Div([
            html.H5("🏪 Ranking das Lojas (Top 25)", className="mb-3"),
            store_table,
            html.Hr(),
            html.H5("👤 Ranking dos Vendedores (Top 25)", className="mb-3 mt-4"),
            seller_table
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro nos rankings: {str(e)}", color="danger")

def generate_lojas_content(df, vouchers_df=None):
    try:
        if df.empty:
            return dbc.Alert("Nenhum dado de lojas disponível.", color="warning")
        
        # Processar dados
        df = df.copy()
        
        # Filtrar Renov
        rede_col = None
        for col in df.columns:
            if 'rede' in col.lower() and 'nome' in col.lower():
                rede_col = col
                break
        
        if rede_col:
            df = df[df[rede_col].str.upper() != 'RENOV']
        
        # Remover horas das datas
        date_columns = ['data_de_inicio', 'data_inicio', 'criado_em', 'data_criacao']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        
        # Identificar colunas de status
        status_col = None
        for col in df.columns:
            if 'status' in col.lower() or 'situacao' in col.lower():
                status_col = col
                break
        
        # Calcular KPIs
        total_lojas = len(df)
        
        # Total de redes ativas
        if status_col and rede_col:
            df_ativas = df[df[status_col].str.lower() == 'ativa'] if status_col in df.columns else df
            total_redes_ativas = df_ativas[rede_col].nunique() if rede_col in df_ativas.columns else 0
        else:
            total_redes_ativas = df[rede_col].nunique() if rede_col else 0
        
        # Lojas sem geração de voucher
        lojas_sem_voucher = 0
        if vouchers_df is not None and not vouchers_df.empty:
            # Filtrar Renov dos vouchers também
            rede_col_voucher = 'nome_da_rede' if 'nome_da_rede' in vouchers_df.columns else 'nome_rede'
            if rede_col_voucher in vouchers_df.columns:
                vouchers_df = vouchers_df[vouchers_df[rede_col_voucher].str.upper() != 'RENOV']
            
            filial_col_voucher = 'nome_da_filial' if 'nome_da_filial' in vouchers_df.columns else 'nome_filial'
            filial_col_loja = 'nome_da_filial' if 'nome_da_filial' in df.columns else 'nome_filial'
            
            if filial_col_voucher in vouchers_df.columns and filial_col_loja in df.columns:
                lojas_com_voucher = set(vouchers_df[filial_col_voucher].unique())
                todas_lojas = set(df[filial_col_loja].unique())
                lojas_sem_voucher = len(todas_lojas - lojas_com_voucher)
        
        # Cards de KPIs
        stats_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total de Lojas", className="card-title text-muted mb-2"),
                        html.H3(f"{total_lojas:,}", className="text-info fw-bold")
                    ])
                ], className="shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Redes Ativas", className="card-title text-muted mb-2"),
                        html.H3(f"{total_redes_ativas:,}", className="text-success fw-bold")
                    ])
                ], className="shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Lojas sem Geração de Voucher", className="card-title text-muted mb-2"),
                        html.H3(f"{lojas_sem_voucher:,}", className="text-warning fw-bold")
                    ])
                ], className="shadow-sm")
            ], md=3)
        ], className="mb-4")
        
        # Gráficos evolutivos
        graphs = []
        
        # Identificar coluna de data
        data_col = None
        for col in ['data_de_inicio', 'data_inicio', 'criado_em', 'data_criacao']:
            if col in df.columns:
                data_col = col
                break
        
        if data_col and status_col:
            # Filtrar apenas ativas
            df_ativas = df[df[status_col].str.lower() == 'ativa'] if status_col in df.columns else df
            
            # Converter para datetime para análise
            df_ativas['data_temp'] = pd.to_datetime(df_ativas[data_col], errors='coerce')
            df_ativas = df_ativas.dropna(subset=['data_temp'])
            
            if not df_ativas.empty:
                # Evolução mensal de redes ativas
                if rede_col:
                    evolucao_redes = df_ativas.groupby([
                        df_ativas['data_temp'].dt.to_period('M'),
                        rede_col
                    ]).size().reset_index(name='count')
                    evolucao_redes['mes'] = evolucao_redes['data_temp'].dt.to_timestamp()
                    evolucao_redes_final = evolucao_redes.groupby('mes')[rede_col].nunique().reset_index()
                    evolucao_redes_final.columns = ['mes', 'total_redes']
                    
                    fig_redes = px.bar(
                        evolucao_redes_final,
                        x='mes',
                        y='total_redes',
                        title='📊 Evolução Mensal - Total de Redes Ativas',
                        labels={'mes': 'Mês', 'total_redes': 'Total de Redes'}
                    )
                    fig_redes.update_layout(height=400)
                    graphs.append(dbc.Col([dcc.Graph(figure=fig_redes)], md=6))
                
                # Evolução mensal de filiais ativas
                evolucao_filiais = df_ativas.groupby(
                    df_ativas['data_temp'].dt.to_period('M')
                ).size().reset_index(name='total_filiais')
                evolucao_filiais['mes'] = evolucao_filiais['data_temp'].dt.to_timestamp()
                
                fig_filiais = px.bar(
                    evolucao_filiais,
                    x='mes',
                    y='total_filiais',
                    title='📊 Evolução Mensal - Total de Filiais Ativas',
                    labels={'mes': 'Mês', 'total_filiais': 'Total de Filiais'}
                )
                fig_filiais.update_layout(height=400)
                graphs.append(dbc.Col([dcc.Graph(figure=fig_filiais)], md=6))
        
        # Preparar dados da tabela
        df_display = df.copy()
        table_columns = [{"name": col.replace('_', ' ').title(), "id": col} for col in df_display.columns]
        
        lojas_table = dash_table.DataTable(
            data=df_display.to_dict('records'),
            columns=table_columns,
            style_cell={'textAlign': 'left', 'fontSize': '12px'},
            style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
            sort_action="native",
            filter_action="native",
            page_size=20,
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ]
        )
        
        return html.Div([
            html.H4("🏪 Base de Lojas", className="mb-4"),
            stats_cards,
            dbc.Row(graphs) if graphs else html.Div(),
            html.Hr(),
            html.P(f"Colunas disponíveis: {', '.join(df.columns.tolist())}", className="text-muted mb-3"),
            lojas_table
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro ao processar base de lojas: {str(e)}", color="danger")filiais = df_ativas.groupby(
                    df_ativas['data_temp'].dt.to_period('M')
                ).size().reset_index(name='total_filiais')
                evolucao_filiais['mes'] = evolucao_filiais['data_temp'].dt.to_timestamp()
                
                fig_filiais = px.bar(
                    evolucao_filiais,
                    x='mes',
                    y='total_filiais',
                    title='📊 Evolução Mensal - Total de Filiais Ativas',
                    labels={'mes': 'Mês', 'total_filiais': 'Total de Filiais'}
                )
                fig_filiais.update_layout(height=400)
                graphs.append(dbc.Col([dcc.Graph(figure=fig_filiais)], md=6))
        
        # Preparar dados da tabela
        df_display = df.copy()
        table_columns = [{"name": col.replace('_', ' ').title(), "id": col} for col in df_display.columns]
        
        lojas_table = dash_table.DataTable(
            data=df_display.to_dict('records'),
            columns=table_columns,
            style_cell={'textAlign': 'left', 'fontSize': '12px'},
            style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
            sort_action="native",
            filter_action="native",
            page_size=20,
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ]
        )
        
        return html.Div([
            html.H4("🏪 Base de Lojas", className="mb-4"),
            stats_cards,
            dbc.Row(graphs) if graphs else html.Div(),
            html.Hr(),
            html.P(f"Colunas disponíveis: {', '.join(df.columns.tolist())}", className="text-muted mb-3"),
            lojas_table
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro ao processar base de lojas: {str(e)}", color="danger")

def generate_colaboradores_content(df):
    try:
        if df.empty:
            return dbc.Alert("Nenhum dado de colaboradores disponível.", color="warning")
        
        # Processar dados
        df = df.copy()
        
        # Filtrar Renov
        rede_col = None
        for col in df.columns:
            if 'rede' in col.lower() and 'nome' in col.lower():
                rede_col = col
                break
        
        if rede_col:
            df = df[df[rede_col].str.upper() != 'RENOV']
        
        # Remover horas das datas
        date_columns = ['data_de_cadastro', 'data_cadastro', 'criado_em', 'data_criacao']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        
        # Identificar coluna de status
        status_col = None
        for col in df.columns:
            if 'status' in col.lower() or 'situacao' in col.lower():
                status_col = col
                break
        
        # Estatísticas gerais
        total_colaboradores = len(df)
        df_ativos = df[df[status_col].str.lower() == 'ativa'] if status_col else df
        total_ativos = len(df_ativos)
        
        stats_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total de Colaboradores", className="card-title text-muted mb-2"),
                        html.H3(f"{total_colaboradores:,}", className="text-success fw-bold")
                    ])
                ], className="shadow-sm")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Colaboradores Ativos", className="card-title text-muted mb-2"),
                        html.H3(f"{total_ativos:,}", className="text-info fw-bold")
                    ])
                ], className="shadow-sm")
            ], md=3)
        ], className="mb-4")
        
        graphs = []
        
        # Gráfico de colaboradores ativos por rede
        if rede_col and status_col:
            colab_por_rede = df_ativos.groupby(rede_col).size().sort_values(ascending=True).tail(15)
            
            fig_redes = px.bar(
                x=colab_por_rede.values,
                y=colab_por_rede.index,
                orientation='h',
                title='👥 Colaboradores Ativos por Rede (Top 15)',
                labels={'x': 'Quantidade de Colaboradores', 'y': 'Rede'},
                color=colab_por_rede.values,
                color_continuous_scale='greens'
            )
            fig_redes.update_layout(height=500)
            graphs.append(dbc.Col([dcc.Graph(figure=fig_redes)], md=6))
        
        # Evolução mensal de colaboradores ativos
        data_col = None
        for col in ['data_de_cadastro', 'data_cadastro', 'criado_em', 'data_criacao']:
            if col in df.columns:
                data_col = col
                break
        
        if data_col and status_col:
            df_ativos['data_temp'] = pd.to_datetime(df[data_col], errors='coerce')
            df_ativos = df_ativos.dropna(subset=['data_temp'])
            
            if not df_ativos.empty:
                evolucao_colab = df_ativos.groupby(
                    df_ativos['data_temp'].dt.to_period('M')
                ).size().reset_index(name='total_colaboradores')
                evolucao_colab['mes'] = evolucao_colab['data_temp'].dt.to_timestamp()
                
                fig_evolucao = px.bar(
                    evolucao_colab,
                    x='mes',
                    y='total_colaboradores',
                    title='📊 Evolução Mensal - Total de Colaboradores Ativos',
                    labels={'mes': 'Mês', 'total_colaboradores': 'Total de Colaboradores'}
                )
                fig_evolucao.update_layout(height=400)
                graphs.append(dbc.Col([dcc.Graph(figure=fig_evolucao)], md=6))
        
        # Preparar dados da tabela
        df_display = df.copy()
        table_columns = [{"name": col.replace('_', ' ').title(), "id": col} for col in df_display.columns]
        
        colaboradores_table = dash_table.DataTable(
            data=df_display.to_dict('records'),
            columns=table_columns,
            style_cell={'textAlign': 'left', 'fontSize': '12px'},
            style_header={'backgroundColor': '#27ae60', 'color': 'white', 'fontWeight': 'bold'},
            sort_action="native",
            filter_action="native",
            page_size=20,
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ]
        )
        
        return html.Div([
            html.H4("👥 Base de Colaboradores", className="mb-4"),
            stats_cards,
            dbc.Row(graphs) if graphs else html.Div(),
            html.Hr(),
            html.P(f"Colunas disponíveis: {', '.join(df.columns.tolist())}", className="text-muted mb-3"),
            colaboradores_table
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro ao processar base de colaboradores: {str(e)}", color="danger")

def generate_projections_content(original_df, filtered_df):
    try:
        df = filtered_df if not filtered_df.empty else original_df
        
        if 'criado_em' not in df.columns:
            return dbc.Alert("Dados temporais não disponíveis para projeções.", color="warning")
        
        # Preparar dados temporais
        df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
        df = df.dropna(subset=['criado_em'])
        
        if df.empty:
            return dbc.Alert("Nenhuma data válida encontrada.", color="warning")
        
        # Análise do período atual
        last_date = df['criado_em'].max()
        current_month = last_date.month
        current_year = last_date.year
        
        current_month_data = df[
            (df['criado_em'].dt.month == current_month) & 
            (df['criado_em'].dt.year == current_year)
        ]
        
        # Identificar colunas
        situacao_col = 'situacao_do_voucher' if 'situacao_do_voucher' in df.columns else 'situacao_voucher'
        valor_col = 'valor_do_dispositivo' if 'valor_do_dispositivo' in df.columns else 'valor_dispositivo'
        
        # Vouchers utilizados
        if situacao_col in current_month_data.columns:
            used_mask = current_month_data[situacao_col].str.upper().str.contains('UTILIZADO', na=False)
            used_vouchers_month = current_month_data[used_mask]
        else:
            used_vouchers_month = pd.DataFrame()
        
        # Calcular métricas
        unique_days = current_month_data['data_str'].nunique() if 'data_str' in current_month_data.columns else 1
        days_in_month = pd.Timestamp(current_year, current_month, 1).days_in_month
        
        vouchers_totais_mes = len(current_month_data)
        vouchers_utilizados_mes = len(used_vouchers_month)
        valor_total_utilizados = used_vouchers_month[valor_col].sum() if valor_col in used_vouchers_month.columns else 0
        
        # Médias e projeções
        media_diaria_totais = vouchers_totais_mes / unique_days if unique_days > 0 else 0
        media_diaria_utilizados = vouchers_utilizados_mes / unique_days if unique_days > 0 else 0
        media_diaria_valor = valor_total_utilizados / unique_days if unique_days > 0 else 0
        
        projecao_vouchers_totais = media_diaria_totais * days_in_month
        projecao_vouchers_utilizados = media_diaria_utilizados * days_in_month
        projecao_valor_total = media_diaria_valor * days_in_month
        
        # Cards de métricas
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
            ], md=3)
        ], className="mb-4")
        
        return html.Div([
            html.H4("🔮 Projeções do Mês Atual", className="mb-4"),
            html.P(f"Período analisado: {unique_days} dias de {pd.Timestamp(current_year, current_month, 1).strftime('%B %Y')}", 
                   className="text-muted mb-4"),
            metrics_cards
        ])
        
    except Exception as e:
        return dbc.Alert(f"Erro nas projeções: {str(e)}", color="danger")

# ========================
# 🔚 Execução
# ========================
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 8080)), host='0.0.0.0')