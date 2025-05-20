
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import base64
import io
import os
import calendar

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard de Resultados"

REQUIRED_COLUMNS = ['Criado em', 'Situacao do voucher', 'Valor do voucher', 'Nome da rede']
COLUMN_ALIASES = {
    'Criado em': ['Criado em', 'Data de criação', 'Data criação'],
    'Situacao do voucher': ['Situacao do voucher', 'Situação do voucher'],
    'Valor do voucher': ['Valor do voucher', 'Valor Voucher', 'Valor'],
    'Nome da rede': ['Nome da rede', 'Rede']
}

def encontrar_coluna_padrao(colunas, nome_padrao):
    for alias in COLUMN_ALIASES[nome_padrao]:
        for col in colunas:
            if col.strip().lower() == alias.strip().lower():
                return col
    return None

def processar_arquivo(contents):
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        df.columns = df.columns.str.strip()

        col_map = {}
        for col in REQUIRED_COLUMNS:
            encontrado = encontrar_coluna_padrao(df.columns, col)
            if encontrado:
                col_map[col] = encontrado
            else:
                raise ValueError(f"Coluna obrigatória não encontrada: {col}")

        df.rename(columns={v: k for k, v in col_map.items()}, inplace=True)
        df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
        df = df[df['Criado em'].notna()]
        df['Mês'] = df['Criado em'].dt.month
        return df
    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")
        return pd.DataFrame()

app.layout = dbc.Container(fluid=True, children=[
    html.H1("Dashboard de Resultados", className="text-center mt-3 mb-4"),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['Arraste ou selecione o arquivo BD.xlsx']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
            'textAlign': 'center', 'marginBottom': '20px'
        },
        multiple=False
    ),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Selecione o mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do Voucher', multi=True), md=4)
    ]),

    html.Div(id='kpi-container', className='my-3'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4)
    ]),

    dcc.Store(id='stored-data')
])

@app.callback(
    Output('stored-data', 'data'),
    Input('upload-data', 'contents')
)
def salvar_dados(contents):
    if contents is None:
        return None
    df = processar_arquivo(contents)
    return df.to_json(date_format='iso', orient='split')

@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Input('stored-data', 'data')
)
def atualizar_filtros(data_json):
    if data_json is None:
        return [], [], []
    df = pd.read_json(data_json, orient='split')
    return (
        [{'label': calendar.month_name[m], 'value': m} for m in sorted(df['Mês'].dropna().unique())],
        [{'label': r, 'value': r} for r in df['Nome da rede'].dropna().unique()],
        [{'label': s, 'value': s} for s in df['Situacao do voucher'].dropna().unique()]
    )

@app.callback(
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Input('stored-data', 'data'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value')
)
def atualizar_dashboard(data_json, mes, rede, situacoes):
    if data_json is None:
        return "", {}, {}, {}

    df = pd.read_json(data_json, orient='split')
    if mes:
        df = df[df['Mês'] == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacoes:
        df = df[df['Situacao do voucher'].isin(situacoes)]

    df_util = df[df['Situacao do voucher'] == 'UTILIZADO']
    total = len(df)
    usados = len(df_util)
    ticket = df_util['Valor do voucher'].mean() if usados else 0
    conversao = (usados / total) * 100 if total else 0

    kpi = html.Div(f"Total: {total} | Utilizados: {usados} | Conversão: {conversao:.2f}% | Ticket Médio: R$ {ticket:,.2f}")

    fig1 = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig2 = px.histogram(df_util, x='Criado em', title='Vouchers Utilizados por Dia')
    fig3 = px.line(df_util.groupby('Criado em')['Valor do voucher'].mean().reset_index(), x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

    return kpi, fig1, fig2, fig3

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
