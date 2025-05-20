
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

app.layout = dbc.Container(fluid=True, children=[
    html.H1("Dashboard de Resultados", style={"textAlign": "center"}),

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
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Selecione Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do Voucher', multi=True), md=4)
    ], className='mb-4'),

    dbc.Row(id='kpi-container', className='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4)
    ])
])

@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Input('upload-data', 'contents')
)
def update_dashboard(contents):
    if not contents:
        return [], [], [], [], {}, {}, {}

    try:
        df = process_data(contents)
    except Exception as e:
        return [], [], [], [html.Div(f"Erro ao processar dados: {str(e)}")], {}, {}, {}

    month_options = [{'label': calendar.month_name[m], 'value': m} for m in sorted(df['Mês'].unique())]
    rede_options = [{'label': r, 'value': r} for r in df['Nome da rede'].dropna().unique()]
    situacoes = [{'label': s, 'value': s} for s in df['Situacao do voucher'].dropna().unique()]

    df_utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']
    total_gerados = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados['Valor do voucher'].sum()
    ticket_medio = df_utilizados['Valor do voucher'].mean() if total_utilizados else 0
    conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0

    kpis = [html.Div(f"Total: {total_gerados} | Utilizados: {total_utilizados} | Conversão: {conversao:.2f}% | Ticket Médio: R$ {ticket_medio:,.2f}")]

    fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(df_utilizados, x='Criado em', title='Vouchers Utilizados por Dia')
    fig_ticket = px.line(df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(), x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

    return month_options, rede_options, situacoes, kpis, fig_gerados, fig_utilizados, fig_ticket

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
