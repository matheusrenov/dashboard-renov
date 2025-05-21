import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import base64
import io
import os
import calendar
from components.kpis import kpi_card

# Configurações iniciais
USERNAME = "admin"
PASSWORD = "senha123"

app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Dashboard de Resultados"

REQUIRED_COLUMNS = [
    'Criado em', 'Situacao do voucher', 'Valor do voucher', 'Nome da rede',
    'Nome do vendedor', 'Nome da filial', 'Descrição', 'Valor do dispositivo',
    'Boost sell in', 'Boost sell out', 'Boost serviço sell out'
]

COLUMN_ALIASES = {
    'Criado em': ['Criado em', 'Data de criação'],
    'Situacao do voucher': ['Situacao do voucher', 'Situação do voucher'],
    'Valor do voucher': ['Valor do voucher', 'Valor'],
    'Nome da rede': ['Nome da rede', 'Rede'],
    'Nome do vendedor': ['Nome do vendedor', 'Vendedor'],
    'Nome da filial': ['Nome da filial', 'Filial'],
    'Descrição': ['Descrição', 'Produto'],
    'Valor do dispositivo': ['Valor do dispositivo'],
    'Boost sell in': ['Boost sell in'],
    'Boost sell out': ['Boost sell out'],
    'Boost serviço sell out': ['Boost serviço sell out']
}

def encontrar_coluna_padrao(colunas, nome_padrao):
    for alias in COLUMN_ALIASES[nome_padrao]:
        for col in colunas:
            if col.strip().lower() == alias.strip().lower():
                return col
    return None

def process_data(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))
    df.columns = df.columns.str.strip()
    col_map = {}
    for padrao in REQUIRED_COLUMNS:
        encontrado = encontrar_coluna_padrao(df.columns, padrao)
        if encontrado:
            col_map[padrao] = encontrado
        else:
            raise ValueError(f"Coluna obrigatória ausente: {padrao}")
    df.rename(columns={v: k for k, v in col_map.items()}, inplace=True)
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df[df['Criado em'].notna()]
    df['Mês'] = df['Criado em'].dt.month
    return df

# Layout de login
login_layout = dbc.Container([
    html.H2("🔒 Acesso ao Painel", className="mb-4", style={"textAlign": "center"}),
    dbc.Row([
        dbc.Col([
            dbc.Input(id="username", placeholder="Usuário", type="text", className="mb-2"),
            dbc.Input(id="password", placeholder="Senha", type="password", className="mb-2"),
            dbc.Button("Entrar", id="login-button", color="primary", className="w-100"),
            html.Div(id="login-output", className="mt-2", style={"color": "red"})
        ], md=4)
    ], justify="center")
], className="mt-5")

# Layout principal do dashboard
dashboard_layout = dbc.Container(fluid=True, children=[
    html.H1("Dashboard de Resultados", style={
        "textAlign": "center", "color": "white",
        "backgroundColor": "black", "padding": "10px"
    }),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['Arraste ou selecione o arquivo BD.xlsx']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
            'textAlign': 'center', 'marginBottom': '20px', 'backgroundColor': '#f9f9f9'
        },
        multiple=False
    ),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Selecione o mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação', multi=True), md=4)
    ], className='mb-4'),

    dcc.Tabs(id='tabs', value='visao-geral', children=[
        dcc.Tab(label='📊 Visão Geral', value='visao-geral'),
        dcc.Tab(label='📈 Performance', value='performance')
    ]),
    html.Div(id='tabs-content'),

    dcc.Store(id='hidden-data'),
    dcc.Store(id='filtered-data')
])

# Layout com controle de rota
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Controle de navegação entre login e dashboard
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/dashboard':
        return dashboard_layout
    else:
        return login_layout

# Verificação de login
@app.callback(
    Output('url', 'pathname'),
    Output('login-output', 'children'),
    Input('login-button', 'n_clicks'),
    State('username', 'value'),
    State('password', 'value'),
    prevent_initial_call=True
)
def login(n_clicks, username, password):
    if username == USERNAME and password == PASSWORD:
        return '/dashboard', ""
    else:
        return dash.no_update, "Usuário ou senha inválidos."

# Upload e filtros
@app.callback(
    Output('hidden-data', 'data'),
    Input('upload-data', 'contents')
)
def carregar_dados(contents):
    if contents is None:
        return dash.no_update
    df = process_data(contents)
    return df.to_json(date_format='iso', orient='split')

@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Input('hidden-data', 'data')
)
def preencher_filtros(json_data):
    if json_data is None:
        return [], [], []
    df = pd.read_json(io.StringIO(json_data), orient='split')
    meses = sorted(df['Mês'].dropna().unique())
    nomes_meses = {i: calendar.month_name[i].capitalize() for i in meses}
    return (
        [{'label': nomes_meses[m], 'value': m} for m in meses],
        [{'label': r, 'value': r} for r in sorted(df['Nome da rede'].dropna().unique())],
        [{'label': s, 'value': s} for s in sorted(df['Situacao do voucher'].dropna().unique())]
    )

@app.callback(
    Output('filtered-data', 'data'),
    Input('hidden-data', 'data'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value')
)
def aplicar_filtros(json_data, mes, rede, situacoes):
    if json_data is None:
        return dash.no_update
    df = pd.read_json(io.StringIO(json_data), orient='split')
    if mes:
        df = df[df['Mês'] == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacoes:
        df = df[df['Situacao do voucher'].isin(situacoes)]
    return df.to_json(date_format='iso', orient='split')

# Renderização dinâmica das abas com KPIs
@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value'),
    Input('filtered-data', 'data')
)
def renderizar_abas(tab, json_data):
    if json_data is None:
        return html.Div("Faça upload de um arquivo para visualizar os dados.")
    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']
    total_gerados = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados['Valor do voucher'].sum()
    valor_total_dispositivo = df_utilizados['Valor do dispositivo'].sum()
    boosts = df_utilizados[['Boost sell in', 'Boost sell out', 'Boost serviço sell out']].fillna(0).sum(axis=1)
    boost_total = boosts.sum()
    ticket_medio = valor_total / total_utilizados if total_utilizados else 0
    custo_medio = valor_total_dispositivo / total_utilizados if total_utilizados else 0
    conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0
    percentual_boost = (boosts.gt(0).sum() / total_utilizados * 100) if total_utilizados else 0

    if tab == "visao-geral":
        kpis = dbc.Row([
            dbc.Col(kpi_card("📦 Dispositivos Captados", str(total_utilizados), "", color="#00C896"), md=3),
            dbc.Col(kpi_card("💰 Captação Total", f"R$ {valor_total:,.2f}", "", color="#00C896"), md=3),
            dbc.Col(kpi_card("📊 Ticket Médio", f"R$ {ticket_medio:,.2f}", "", color="#00C896"), md=3),
            dbc.Col(kpi_card("📈 Conversão", f"{conversao:.2f}%", "", color="#00C896"), md=3),
            dbc.Col(kpi_card("📱 Valor Dispositivo", f"R$ {valor_total_dispositivo:,.2f}", "", color="#00C896"), md=3),
            dbc.Col(kpi_card("📉 Custo Médio", f"R$ {custo_medio:,.2f}", "", color="#00C896"), md=3),
            dbc.Col(kpi_card("⚡ Boost Total", f"R$ {boost_total:,.2f}", "", color="#00C896"), md=3),
            dbc.Col(kpi_card("🔥 % Boost", f"{percentual_boost:.2f}%", "", color="#00C896"), md=3),
        ], className="mb-4")

        fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
        fig_utilizados = px.histogram(df_utilizados, x='Criado em', title='Vouchers Utilizados por Dia')
        fig_ticket = px.line(df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(), x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

        for fig in [fig_gerados, fig_utilizados, fig_ticket]:
            fig.update_layout(template='plotly_dark', plot_bgcolor='rgba(0,0,0,0)')

        return html.Div([
            kpis,
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
                dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
                dbc.Col(dcc.Graph(figure=fig_ticket), md=4)
            ])
        ])

    elif tab == "performance":
        ranking_df = df_utilizados.groupby(['Nome do vendedor', 'Nome da filial', 'Nome da rede']) \
            .size().reset_index(name='Quantidade')
        ranking_df['Ranking'] = ranking_df['Quantidade'].rank(method='first', ascending=False).astype(int)
        ranking_df = ranking_df.sort_values('Ranking')
        top_vendedores_data = ranking_df.to_dict('records')
        top_vendedores_columns = [{'name': col, 'id': col} for col in ranking_df.columns]

        top_dispositivos_df = df['Descrição'].value_counts().nlargest(10).reset_index()
        top_dispositivos_df.columns = ['Descrição', 'Quantidade']
        fig_dispositivos = px.bar(top_dispositivos_df, x='Descrição', y='Quantidade', text='Quantidade', title='Top Dispositivos')
        fig_dispositivos.update_traces(textposition='outside')
        fig_dispositivos.update_layout(template='plotly_dark')

        campanha_cols = ['Boost sell in', 'Boost sell out', 'Boost serviço sell out']
        campanha_sum = df_utilizados[campanha_cols].fillna(0).sum().reset_index()
        campanha_sum.columns = ['Campanha', 'Valor']
        fig_campanhas = px.bar(campanha_sum, x='Campanha', y='Valor', title='Campanhas com Boost')
        fig_campanhas.update_layout(template='plotly_dark')

        return html.Div([
            dbc.Row([
                dbc.Col(dash_table.DataTable(data=top_vendedores_data, columns=top_vendedores_columns, style_table={'overflowX': 'auto'}), md=6),
                dbc.Col(dcc.Graph(figure=fig_dispositivos), md=6)
            ], className='mb-4'),
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_campanhas), md=12)
            ])
        ])

    return html.Div("Erro ao carregar aba.")

if __name__ == '__main__':
    app.run(server=server, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

