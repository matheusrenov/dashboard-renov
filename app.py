
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import base64
import io
import dash_bootstrap_components as dbc
import os

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard de Resultados"

REQUIRED_COLUMNS = ['Criado em', 'Situacao do voucher', 'Valor do voucher', 'Nome da rede', 'Nome do vendedor']

app.layout = dbc.Container(fluid=True, children=[
    html.H1("Dashboard de Resultados", style={"textAlign": "center", "color": "black"}),

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
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do Voucher', multi=True), md=4)
    ], className='mb-4'),

    html.Div(id='kpi-container', className='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4)
    ], className='mb-4'),

    dbc.Row([
        dbc.Col(html.Div(id='top-vendedores'), md=6)
    ], className='mb-4'),

    dcc.Store(id='hidden-data'),
    dcc.Store(id='filtered-data')
])

@app.callback(
    Output('hidden-data', 'data'),
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Input('upload-data', 'contents')
)
def carregar_dados(contents):
    if contents is None:
        return None, [], [], []

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))

    if not all(col in df.columns for col in REQUIRED_COLUMNS):
        raise ValueError("Planilha com colunas obrigatórias ausentes.")

    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df[df['Criado em'].notna()]
    df['Mês'] = df['Criado em'].dt.month_name()

    options_mes = [{'label': m, 'value': m} for m in sorted(df['Mês'].unique())]
    options_rede = [{'label': r, 'value': r} for r in sorted(df['Nome da rede'].dropna().unique())]
    options_situacao = [{'label': s, 'value': s} for s in sorted(df['Situacao do voucher'].dropna().unique())]

    return df.to_json(date_format='iso', orient='split'), options_mes, options_rede, options_situacao

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

@app.callback(
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Output('top-vendedores', 'children'),
    Input('filtered-data', 'data')
)
def update_dashboard(json_data):
    if json_data is None:
        return [dash.no_update] * 5

    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']

    total_gerados = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados['Valor do voucher'].sum()
    ticket_medio = df_utilizados['Valor do voucher'].mean() if total_utilizados else 0
    conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0

    kpis = html.Div(f"Total: {total_gerados} | Utilizados: {total_utilizados} | Conversão: {conversao:.2f}% | Ticket Médio: R$ {ticket_medio:,.2f}")

    fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(df_utilizados, x='Criado em', title='Vouchers Utilizados por Dia')
    fig_ticket = px.line(df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(), x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

    top_vendedores = dash_table.DataTable(columns=[{'name': i, 'id': i} for i in ['Nome do vendedor', 'Quantidade']],
                                          data=df_utilizados['Nome do vendedor'].value_counts().reset_index().rename(columns={'index': 'Nome do vendedor', 'Nome do vendedor': 'Quantidade'}).to_dict('records'))

    return kpis, fig_gerados, fig_utilizados, fig_ticket, top_vendedores

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
