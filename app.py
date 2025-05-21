import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import io, base64, os

from components.kpis import kpi_card

# Login padrão
USERNAME = "admin"
PASSWORD = "senha123"

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

app.title = "Dashboard de Resultados"

app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Store(id="auth-store", storage_type="session"),
    html.Div(id="page-content")
])

# Página de login
login_layout = dbc.Container([
    html.H2("Acesso Restrito", className="text-center mt-4"),
    dbc.Row([
        dbc.Col([
            dbc.Input(id="username", placeholder="Usuário", type="text", className="mb-2"),
            dbc.Input(id="password", placeholder="Senha", type="password", className="mb-2"),
            dbc.Button("Entrar", id="login-button", color="primary", className="w-100"),
            html.Div(id="login-alert", className="text-danger mt-2")
        ], width=4)
    ], justify="center")
], fluid=True)

# Página principal (dashboard)
dashboard_layout = dbc.Container([
    html.H2("Dashboard de Resultados", className="text-center my-4"),

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
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do voucher', multi=True), md=4),
    ], className='mb-4'),

    dbc.Row(id='kpi-container', className='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4)
    ], className='mb-4'),

    dbc.Row([
        dbc.Col(dash_table.DataTable(id='top-vendedores', style_table={'overflowX': 'auto'}), md=6),
        dbc.Col(dcc.Graph(id='top-dispositivos'), md=6)
    ]),

    dcc.Store(id='hidden-data'),
    dcc.Store(id='filtered-data')
], fluid=True)

# Roteamento
@app.callback(Output("page-content", "children"),
              Input("url", "pathname"),
              State("auth-store", "data"))
def route(path, authed):
    if authed == "ok":
        return dashboard_layout
    return login_layout

# Login handler
@app.callback(
    Output("auth-store", "data"),
    Output("url", "pathname"),
    Output("login-alert", "children"),
    Input("login-button", "n_clicks"),
    State("username", "value"),
    State("password", "value"),
    prevent_initial_call=True
)
def login(n, user, pw):
    if user == USERNAME and pw == PASSWORD:
        return "ok", "/", ""
    return None, "/login", "Usuário ou senha inválidos."

# Upload + leitura segura
def process_data(contents):
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        df.columns = df.columns.str.strip()
        df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
        df = df[df['Criado em'].notna()]
        df['Mês'] = df['Criado em'].dt.month_name(locale='pt_BR')
        return df
    except Exception as e:
        print(f"Erro ao processar: {e}")
        return None

@app.callback(Output('hidden-data', 'data'), Input('upload-data', 'contents'))
def carregar_dados(contents):
    if contents is None:
        return None
    df = process_data(contents)
    return df.to_json(date_format='iso', orient='split') if df is not None else None

@app.callback(
    Output('filtered-data', 'data'),
    Input('hidden-data', 'data'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value')
)
def aplicar_filtros(json_data, mes, rede, situacoes):
    if json_data is None:
        return None
    df = pd.read_json(io.StringIO(json_data), orient='split')
    if mes:
        df = df[df['Mês'] == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacoes:
        df = df[df['Situacao do voucher'].isin(situacoes)]
    return df.to_json(date_format='iso', orient='split')

@app.callback(
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Output('top-vendedores', 'data'),
    Output('top-vendedores', 'columns'),
    Output('top-dispositivos', 'figure'),
    Input('filtered-data', 'data')
)
def update_dashboard(json_data):
    if json_data is None:
        return ["Aguardando dados..."], {}, {}, {}, [], [], {}

    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_util = df[df['Situacao do voucher'] == 'UTILIZADO']

    total = len(df)
    utilizados = len(df_util)
    total_valor = df_util['Valor do voucher'].sum()
    ticket = df_util['Valor do voucher'].mean() if utilizados else 0
    conv = (utilizados / total) * 100 if total else 0

    kpis = dbc.Row([
        dbc.Col(kpi_card("Dispositivos Captados", utilizados, "", icon="📦"), md=3),
        dbc.Col(kpi_card("Captação Total", f"R$ {total_valor:,.2f}", "", icon="💰"), md=3),
        dbc.Col(kpi_card("Ticket Médio", f"R$ {ticket:,.2f}", "", icon="📊"), md=3),
        dbc.Col(kpi_card("Conversão", f"{conv:.2f}%", "", icon="📈"), md=3)
    ])

    fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(df_util, x='Criado em', title='Vouchers Utilizados por Dia')
    fig_ticket = px.line(df_util.groupby('Criado em')['Valor do voucher'].mean().reset_index(), x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

    ranking = df_util.groupby(['Nome do vendedor', 'Nome da filial', 'Nome da rede']).size().reset_index(name='Quantidade')
    ranking = ranking.sort_values(by='Quantidade', ascending=False).head(10)
    top_data = ranking.to_dict('records')
    top_cols = [{"name": i, "id": i} for i in ranking.columns]

    top_descr = df['Descrição'].value_counts().nlargest(10).reset_index()
    top_descr.columns = ['Descrição', 'Quantidade']
    fig_descr = px.bar(top_descr, x='Descrição', y='Quantidade', title='Top Dispositivos')

    return kpis, fig_gerados, fig_utilizados, fig_ticket, top_data, top_cols, fig_descr

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
