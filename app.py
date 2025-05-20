
import dash
from dash import dcc, html, dash_table, ctx
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import datetime
import base64
import io
import os

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard de Resultados"

REQUIRED_COLUMNS = ['Criado em', 'Situacao do voucher', 'Valor do voucher', 'Nome da rede']

COLUMN_ALIASES = {
    'Criado em': ['Criado em', 'Data de criação', 'Data criação'],
    'Situacao do voucher': ['Situacao do voucher', 'Situação do voucher', 'Situação Voucher', 'Status do voucher'],
    'Valor do voucher': ['Valor do voucher', 'Valor Voucher', 'Valor'],
    'Nome da rede': ['Nome da rede', 'Rede', 'Nome Rede']
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

    df.columns = df.columns.str.strip().str.lower()

    col_map = {}
    for padrao in REQUIRED_COLUMNS:
        found = encontrar_coluna_padrao(df.columns, padrao)
        if found:
            col_map[padrao] = found
        else:
            raise ValueError(f"Coluna obrigatória ausente: {padrao}")

    df.rename(columns={v: k for k, v in col_map.items()}, inplace=True)
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df[df['Criado em'].notna()]
    df['Mês'] = df['Criado em'].dt.month

    return df

app.layout = dbc.Container(fluid=True, children=[
    html.H1("Dashboard de Resultados", style={"textAlign": "center", "color": "white", "backgroundColor": "black", "padding": "10px"}),

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
    ], className='mb-4'),

    dbc.Row([
        dbc.Col(html.Div(id='top-filiais'), md=6),
        dbc.Col(html.Div(id='top-vendedores'), md=6)
    ], className='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='top-dispositivos'), md=12)
    ]),

    dcc.Store(id='hidden-data'),
    dcc.Store(id='filtered-data')
])

@app.callback(
    Output('hidden-data', 'data'),
    Input('upload-data', 'contents')
)
def upload(contents):
    if contents is None:
        return dash.no_update
    df = process_data(contents)
    return df.to_json(date_format='iso', orient='split')

@app.callback(
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Output('top-filiais', 'children'),
    Output('top-vendedores', 'children'),
    Output('top-dispositivos', 'figure'),
    Input('filtered-data', 'data')
)
def update_dashboard(json_data):
    if json_data is None:
        return [dash.no_update] * 7

    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']
    total_gerados = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados['Valor do voucher'].sum()
    ticket_medio = df_utilizados['Valor do voucher'].mean() if total_utilizados else 0
    conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0

    kpis = [html.Div(f"Total Gerados: {total_gerados} | Utilizados: {total_utilizados} | Conversão: {conversao:.2f}% | Ticket Médio: R$ {ticket_medio:,.2f}")]

    fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(df_utilizados, x='Criado em', title='Vouchers Utilizados por Dia')
    fig_ticket = px.line(df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(), x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

    # Proteções para colunas ausentes
    if 'Nome do vendedor' in df_utilizados.columns:
        top_vendedores = dash_table.DataTable(
            columns=[{'name': 'Nome do vendedor', 'id': 'Nome do vendedor'}, {'name': 'Quantidade', 'id': 'Quantidade'}],
            data=df_utilizados['Nome do vendedor'].value_counts().reset_index().rename(columns={'index': 'Nome do vendedor', 'Nome do vendedor': 'Quantidade'}).to_dict('records')
        )
    else:
        top_vendedores = html.Div("Coluna 'Nome do vendedor' não encontrada.")

    if 'Descrição' in df.columns:
        top_dispositivos = px.bar(
            df['Descrição'].value_counts().nlargest(10).reset_index(),
            x='index', y='Descrição', title='Top 10 Dispositivos Mais Avaliados'
        )
    else:
        top_dispositivos = go.Figure().update_layout(title="Coluna 'Descrição' não encontrada.")

    top_filiais = dash_table.DataTable(
        columns=[{'name': 'Nome da rede', 'id': 'Nome da rede'}, {'name': 'Quantidade', 'id': 'Quantidade'}],
        data=df_utilizados['Nome da rede'].value_counts().reset_index().rename(columns={'index': 'Nome da rede', 'Nome da rede': 'Quantidade'}).to_dict('records')
    )

    return kpis, fig_gerados, fig_utilizados, fig_ticket, top_filiais, top_vendedores, top_dispositivos


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

