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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Armazenamento global seguro
app.df_original = None

# ========================
# 🎨 Layout Melhorado
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

    # Controles principais
    dbc.Row([
        dbc.Col([
            dcc.Upload(
                id="upload-data",
                children=dbc.Button([
                    html.I(className="fas fa-upload me-2"),
                    "Importar Planilha Base"
                ], color="primary", size="lg", className="w-100"),
                accept=".xlsx,.xls",
                multiple=False,
                style={'width': '100%'}
            )
        ], md=8),
        dbc.Col([
            dbc.Button([
                html.I(className="fas fa-file-pdf me-2"),
                "Exportar PDF"
            ], id="export-pdf", color="success", size="lg", className="w-100")
        ], md=4)
    ], className="mb-4"),

    # Alertas e mensagens
    html.Div(id='alert-container'),

    # Filtros
    html.Div(id='filtros-container'),

    # Store para dados filtrados
    dcc.Store(id='dados-filtrados'),

    # KPIs
    html.Div(id='kpi-container', className="mb-4"),

    # Abas para organizar conteúdo
    dcc.Tabs(id="tabs", value="tab-geral", children=[
        dcc.Tab(label="📈 Visão Geral", value="tab-geral"),
        dcc.Tab(label="📅 Análise Temporal", value="tab-temporal"),
        dcc.Tab(label="🏪 Análise por Rede", value="tab-rede"),
        dcc.Tab(label="🔄 Fluxo de Processo", value="tab-fluxo"),
        dcc.Tab(label="🏆 Rankings", value="tab-ranking")
    ], className="mb-4"),

    # Conteúdo das abas
    html.Div(id='tab-content'),

], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'padding': '20px'})

# ========================
# 📥 CALLBACK PRINCIPAL - Upload e Processamento
# ========================
@app.callback(
    [Output('alert-container', 'children'),
     Output('filtros-container', 'children'),
     Output('dados-filtrados', 'data')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')],
    prevent_initial_call=True
)
def processar_upload(contents, filename):
    if not contents:
        return "", "", {}

    try:
        # Decodificar arquivo
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        # Normalizar colunas
        df.columns = [unidecode(str(col)).strip().lower().replace(' ', '_') for col in df.columns]
        
        # Verificar colunas obrigatórias
        colunas_necessarias = {
            'imei': ['imei'],
            'criado_em': ['criado_em', 'data_criacao', 'data'],
            'valor_voucher': ['valor_do_voucher', 'valor_voucher'],
            'valor_dispositivo': ['valor_do_dispositivo', 'valor_dispositivo'],
            'situacao_voucher': ['situacao_do_voucher', 'situacao_voucher', 'status'],
            'nome_vendedor': ['nome_do_vendedor', 'vendedor'],
            'nome_filial': ['nome_da_filial', 'filial'],
            'nome_rede': ['nome_da_rede', 'rede']
        }

        # Mapear colunas
        mapeamento = {}
        for col_standard, col_variants in colunas_necessarias.items():
            encontrada = False
            for variant in col_variants:
                if variant in df.columns:
                    mapeamento[variant] = col_standard
                    encontrada = True
                    break
            if not encontrada:
                return (
                    dbc.Alert(f"❌ Coluna não encontrada: {col_standard}. Variações aceitas: {col_variants}", 
                             color="danger"),
                    "", {}
                )

        # Renomear colunas
        df = df.rename(columns=mapeamento)

        # Processar dados
        df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
        df = df.dropna(subset=['criado_em'])  # Remove linhas com data inválida
        
        df['mes'] = df['criado_em'].dt.strftime('%b')
        df['mes_num'] = df['criado_em'].dt.month
        df['dia'] = df['criado_em'].dt.day
        df['ano'] = df['criado_em'].dt.year

        # Limpar dados
        df['valor_voucher'] = pd.to_numeric(df['valor_voucher'], errors='coerce').fillna(0)
        df['valor_dispositivo'] = pd.to_numeric(df['valor_dispositivo'], errors='coerce').fillna(0)

        # Salvar dados originais
        app.df_original = df

        # Criar filtros
        filtros = criar_filtros(df)

        # Sucesso
        alert = dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"✅ Arquivo '{filename}' carregado com sucesso! {len(df)} registros processados."
        ], color="success", dismissable=True)

        return alert, filtros, df.to_dict('records')

    except Exception as e:
        return (
            dbc.Alert(f"❌ Erro ao processar arquivo: {str(e)}", color="danger"),
            "", {}
        )

# ========================
# 🔧 FUNÇÃO PARA CRIAR FILTROS
# ========================
def criar_filtros(df):
    return dbc.Card([
        dbc.CardHeader(html.H5("🔍 Filtros", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Mês:", className="fw-bold"),
                    dcc.Dropdown(
                        id='filtro-mes',
                        options=[{'label': f"{m} ({df[df['mes']==m]['ano'].iloc[0]})", 'value': m} 
                                for m in sorted(df['mes'].unique(), 
                                              key=lambda x: datetime.strptime(x, "%b").month)],
                        multi=True,
                        placeholder="Selecionar meses..."
                    )
                ], md=3),
                dbc.Col([
                    html.Label("Rede:", className="fw-bold"),
                    dcc.Dropdown(
                        id='filtro-rede',
                        options=[{'label': r, 'value': r} 
                                for r in sorted(df['nome_rede'].dropna().unique())],
                        multi=True,
                        placeholder="Selecionar redes..."
                    )
                ], md=3),
                dbc.Col([
                    html.Label("Situação:", className="fw-bold"),
                    dcc.Dropdown(
                        id='filtro-situacao',
                        options=[{'label': s, 'value': s} 
                                for s in sorted(df['situacao_voucher'].dropna().unique())],
                        multi=True,
                        placeholder="Selecionar situações..."
                    )
                ], md=3),
                dbc.Col([
                    html.Label("Vendedor:", className="fw-bold"),
                    dcc.Dropdown(
                        id='filtro-vendedor',
                        options=[{'label': v, 'value': v} 
                                for v in sorted(df['nome_vendedor'].dropna().unique())],
                        multi=True,
                        placeholder="Selecionar vendedores..."
                    )
                ], md=3)
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Button("🔄 Limpar Filtros", id="limpar-filtros", 
                              color="outline-secondary", size="sm", className="mt-2")
                ])
            ])
        ])
    ], className="mb-4")

# ========================
# 🔄 CALLBACK PARA FILTROS
# ========================
@app.callback(
    Output('dados-filtrados', 'data'),
    [Input('filtro-mes', 'value'),
     Input('filtro-rede', 'value'),
     Input('filtro-situacao', 'value'),
     Input('filtro-vendedor', 'value'),
     Input('limpar-filtros', 'n_clicks')],
    prevent_initial_call=True
)
def aplicar_filtros(meses, redes, situacoes, vendedores, limpar_clicks):
    if app.df_original is None:
        return {}
    
    ctx = callback_context
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'limpar-filtros.n_clicks':
        return app.df_original.to_dict('records')
    
    df = app.df_original.copy()
    
    if meses:
        df = df[df['mes'].isin(meses)]
    if redes:
        df = df[df['nome_rede'].isin(redes)]
    if situacoes:
        df = df[df['situacao_voucher'].isin(situacoes)]
    if vendedores:
        df = df[df['nome_vendedor'].isin(vendedores)]
    
    return df.to_dict('records')

# ========================
# 📊 CALLBACK PARA KPIs
# ========================
@app.callback(
    Output('kpi-container', 'children'),
    [Input('dados-filtrados', 'data')],
    prevent_initial_call=True
)
def atualizar_kpis(dados):
    if not dados:
        return ""
    
    df = pd.DataFrame(dados)
    return gerar_kpis(df)

# ========================
# 📈 CALLBACK PARA CONTEÚDO DAS ABAS
# ========================
@app.callback(
    Output('tab-content', 'children'),
    [Input('tabs', 'value'),
     Input('dados-filtrados', 'data')],
    prevent_initial_call=True
)
def atualizar_conteudo_aba(tab_ativa, dados):
    if not dados:
        return dbc.Alert("📤 Carregue uma planilha para visualizar os dados", color="info")
    
    df = pd.DataFrame(dados)
    
    if tab_ativa == "tab-geral":
        return gerar_visao_geral(df)
    elif tab_ativa == "tab-temporal":
        return gerar_analise_temporal(df)
    elif tab_ativa == "tab-rede":
        return gerar_analise_rede(df)
    elif tab_ativa == "tab-fluxo":
        return gerar_fluxo_processo(df)
    elif tab_ativa == "tab-ranking":
        return gerar_rankings(df)
    
    return ""

# ========================
# 📊 FUNÇÕES DE GERAÇÃO DE GRÁFICOS
# ========================
def gerar_kpis(df):
    total = len(df)
    usados = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
    captados = len(usados)
    
    valor_total = usados['valor_dispositivo'].sum()
    ticket_medio = valor_total / captados if captados > 0 else 0
    conversao = (captados / total * 100) if total > 0 else 0
    
    # Cálculos de projeção
    if not df.empty:
        mes_atual = df['criado_em'].dt.to_period('M').mode().iloc[0] if len(df) > 0 else None
        if mes_atual:
            dados_mes = df[df['criado_em'].dt.to_period('M') == mes_atual]
            dias_transcorridos = dados_mes['dia'].nunique()
            media_diaria = len(dados_mes) / dias_transcorridos if dias_transcorridos > 0 else 0
            projecao_mensal = media_diaria * 30
        else:
            media_diaria = projecao_mensal = 0
    else:
        media_diaria = projecao_mensal = 0

    def criar_card_kpi(titulo, valor, cor="primary", media=None, projecao=None):
        children = [
            html.H6(titulo, className="card-title text-muted"),
            html.H3(valor, className=f"text-{cor} fw-bold")
        ]
        if media is not None:
            children.extend([
                html.Hr(),
                html.Small(f"📈 Média diária: {media:,.0f}", className="text-muted"),
                html.Br(),
                html.Small(f"📊 Projeção mensal: {projecao:,.0f}", className="text-muted")
            ])
        
        return dbc.Col([
            dbc.Card([
                dbc.CardBody(children)
            ], className="h-100 shadow-sm")
        ], md=2)

    return dbc.Row([
        criar_card_kpi("Vouchers Gerados", f"{total:,}", "info", media_diaria, projecao_mensal),
        criar_card_kpi("Dispositivos Captados", f"{captados:,}", "success"),
        criar_card_kpi("Valor Total Captado", f"R$ {valor_total:,.2f}", "warning"),
        criar_card_kpi("Ticket Médio", f"R$ {ticket_medio:,.2f}", "primary"),
        criar_card_kpi("Taxa de Conversão", f"{conversao:.1f}%", "danger")
    ], className="g-3")

def gerar_visao_geral(df):
    if df.empty:
        return dbc.Alert("Nenhum dado disponível", color="warning")
    
    # Distribuição por situação
    situacao_counts = df['situacao_voucher'].value_counts()
    fig_pizza = px.pie(values=situacao_counts.values, names=situacao_counts.index,
                      title="📊 Distribuição por Situação do Voucher")
    fig_pizza.update_traces(textposition='inside', textinfo='percent+label')
    
    # Top 5 redes
    top_redes = df['nome_rede'].value_counts().head(5)
    fig_redes = px.bar(x=top_redes.values, y=top_redes.index, orientation='h',
                      title="🏪 Top 5 Redes por Volume", labels={'x': 'Quantidade', 'y': 'Rede'})
    fig_redes.update_layout(yaxis={'categoryorder': 'total ascending'})
    
    return dbc.Row([
        dbc.Col([dcc.Graph(figure=fig_pizza)], md=6),
        dbc.Col([dcc.Graph(figure=fig_redes)], md=6)
    ])

def gerar_analise_temporal(df):
    if df.empty:
        return dbc.Alert("Nenhum dado disponível", color="warning")
    
    # Série temporal diária
    df['data'] = df['criado_em'].dt.date
    serie_diaria = df.groupby('data').size().reset_index(name='quantidade')
    
    fig_linha = px.line(serie_diaria, x='data', y='quantidade',
                       title="📅 Vouchers Gerados por Dia")
    fig_linha.update_traces(line_color='#3498db', line_width=3)
    
    # Heatmap por dia da semana e hora (se houver hora)
    df['dia_semana'] = df['criado_em'].dt.day_name()
    df['hora'] = df['criado_em'].dt.hour
    
    heatmap_data = df.groupby(['dia_semana', 'hora']).size().unstack(fill_value=0)
    
    if not heatmap_data.empty:
        fig_heatmap = px.imshow(heatmap_data.values, 
                              x=heatmap_data.columns, 
                              y=heatmap_data.index,
                              title="🔥 Heatmap: Dia da Semana vs Hora",
                              labels={'x': 'Hora', 'y': 'Dia da Semana', 'color': 'Quantidade'})
    else:
        fig_heatmap = go.Figure().add_annotation(text="Dados insuficientes para heatmap")
    
    return dbc.Row([
        dbc.Col([dcc.Graph(figure=fig_linha)], md=12),
        dbc.Col([dcc.Graph(figure=fig_heatmap)], md=12)
    ])

def gerar_analise_rede(df):
    if df.empty:
        return dbc.Alert("Nenhum dado disponível", color="warning")
    
    # Performance por rede
    rede_stats = df.groupby('nome_rede').agg({
        'imei': 'count',
        'valor_dispositivo': 'sum',
        'valor_voucher': 'mean'
    }).round(2)
    rede_stats.columns = ['Total_Vouchers', 'Valor_Total', 'Ticket_Medio']
    rede_stats = rede_stats.reset_index()
    
    fig_scatter = px.scatter(rede_stats, x='Total_Vouchers', y='Valor_Total', 
                           size='Ticket_Medio', hover_name='nome_rede',
                           title="💰 Performance das Redes: Volume vs Valor")
    
    return dbc.Row([
        dbc.Col([dcc.Graph(figure=fig_scatter)], md=12),
        dbc.Col([
            html.H5("📋 Detalhamento por Rede"),
            dash_table.DataTable(
                data=rede_stats.to_dict('records'),
                columns=[{"name": i, "id": i, "type": "numeric", "format": {"specifier": ",.0f"}} 
                        for i in rede_stats.columns],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f8f9fa'
                    }
                ],
                sort_action="native",
                page_size=10
            )
        ], md=12)
    ])

def gerar_fluxo_processo(df):
    if df.empty:
        return dbc.Alert("Nenhum dado disponível", color="warning")
    
    # Sankey diagram
    usados = df[df['situacao_voucher'].str.lower().str.contains('utilizado|usado|ativo', na=False)]
    
    total_vouchers = len(df)
    total_usados = len(usados)
    
    labels = ['Vouchers Criados', 'Vouchers Utilizados']
    sources = [0]
    targets = [1]
    values = [total_usados]
    
    # Adicionar breakdown por rede
    rede_counts = usados['nome_rede'].value_counts()
    for i, (rede, count) in enumerate(rede_counts.items()):
        labels.append(f"{rede}")
        sources.append(1)
        targets.append(len(labels) - 1)
        values.append(count)
    
    fig_sankey = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=labels,
            color="lightblue"
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values
        )
    )])
    
    fig_sankey.update_layout(title_text="🔄 Fluxo do Processo", font_size=12)
    
    return dcc.Graph(figure=fig_sankey)

def gerar_rankings(df):
    if df.empty:
        return dbc.Alert("Nenhum dado disponível", color="warning")
    
    # Top vendedores
    vendedor_stats = df.groupby(['nome_vendedor', 'nome_filial', 'nome_rede']).agg({
        'imei': 'count',
        'valor_dispositivo': 'sum'
    }).round(2)
    vendedor_stats.columns = ['Total_Vouchers', 'Valor_Total']
    vendedor_stats = vendedor_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(15)
    
    # Top filiais
    filial_stats = df.groupby(['nome_filial', 'nome_rede']).agg({
        'imei': 'count',
        'valor_dispositivo': 'sum'
    }).round(2)
    filial_stats.columns = ['Total_Vouchers', 'Valor_Total']
    filial_stats = filial_stats.reset_index().sort_values('Total_Vouchers', ascending=False).head(10)
    
    return dbc.Row([
        dbc.Col([
            html.H5("🏆 Top 15 Vendedores"),
            dash_table.DataTable(
                data=vendedor_stats.to_dict('records'),
                columns=[{"name": i.replace('_', ' ').title(), "id": i} for i in vendedor_stats.columns],
                style_cell={'textAlign': 'left', 'fontSize': '12px'},
                style_header={'backgroundColor': '#28a745', 'color': 'white', 'fontWeight': 'bold'},
                page_size=15,
                sort_action="native"
            )
        ], md=6),
        dbc.Col([
            html.H5("🏪 Top 10 Filiais"),
            dash_table.DataTable(
                data=filial_stats.to_dict('records'),
                columns=[{"name": i.replace('_', ' ').title(), "id": i} for i in filial_stats.columns],
                style_cell={'textAlign': 'left', 'fontSize': '12px'},
                style_header={'backgroundColor': '#007bff', 'color': 'white', 'fontWeight': 'bold'},
                page_size=10,
                sort_action="native"
            )
        ], md=6)
    ])

# ========================
# 🔚 Execução
# ========================
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 8080)), host='0.0.0.0')