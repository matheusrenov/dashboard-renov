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
from components.kpis import kpi_card

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard de Resultados"

REQUIRED_COLUMNS = ['Criado em', 'Situacao do voucher', 'Valor do voucher', 'Nome da rede', 'Nome do vendedor', 'Nome da filial', 'Descrição']

COLUMN_ALIASES = {
    'Criado em': ['Criado em', 'Data de criação', 'Data criação'],
    'Situacao do voucher': ['Situacao do voucher', 'Situação do voucher'],
    'Valor do voucher': ['Valor do voucher', 'Valor Voucher', 'Valor'],
    'Nome da rede': ['Nome da rede', 'Rede'],
    'Nome do vendedor': ['Nome do vendedor', 'Vendedor'],
    'Nome da filial': ['Nome da filial', 'Filial'],
    'Descrição': ['Descrição', 'Descricao', 'Produto']
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
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Vouchers Gerados por Dia"),
                dbc.CardBody(dcc.Graph(id='vouchers-gerados'))
            ], className="h-100 shadow-sm"),
            md=4
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Vouchers Utilizados por Dia"),
                dbc.CardBody(dcc.Graph(id='vouchers-utilizados'))
            ], className="h-100 shadow-sm"),
            md=4
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Ticket Médio Diário"),
                dbc.CardBody(dcc.Graph(id='ticket-medio'))
            ], className="h-100 shadow-sm"),
            md=4
        )
    ], className='mb-4'),

    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Ranking de Vendedores"),
                dbc.CardBody(dash_table.DataTable(id='top-vendedores', style_table={'overflowX': 'auto'}))
            ], className="shadow-sm"),
            md=6
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Top 10 Dispositivos Mais Avaliados"),
                dbc.CardBody(dcc.Graph(id='top-dispositivos'))
            ], className="shadow-sm"),
            md=6
        )
    ], className='mb-4'),

    dcc.Store(id='hidden-data'),
    dcc.Store(id='filtered-data')
])

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
        return [dash.no_update] * 7

    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']

    total_gerados = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados['Valor do voucher'].sum()
    ticket_medio = df_utilizados['Valor do voucher'].mean() if total_utilizados else 0
    conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0

    kpis = [
        dbc.Col(kpi_card("📦 Dispositivos Captados", str(total_utilizados), "", color="#00C896"), md=3),
        dbc.Col(kpi_card("💰 Captação Total", f"R$ {valor_total:,.2f}", "", color="#00C896"), md=3),
        dbc.Col(kpi_card("📊 Ticket Médio", f"R$ {ticket_medio:,.2f}", "", color="#00C896"), md=3),
        dbc.Col(kpi_card("📈 Taxa de Conversão", f"{conversao:.2f}" + "%", "", color="#00C896"), md=3)
    ]

    fig_gerados = px.histogram(df, x='Criado em')
    fig_gerados.update_layout(template='plotly_dark', title='Vouchers Gerados por Dia')

    fig_utilizados = px.histogram(df_utilizados, x='Criado em')
    fig_utilizados.update_layout(template='plotly_dark', title='Vouchers Utilizados por Dia')

    fig_ticket = px.line(
        df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(),
        x='Criado em',
        y='Valor do voucher'
    )
    fig_ticket.update_layout(template='plotly_dark', title='Ticket Médio Diário')

    ranking_df = df_utilizados.groupby(['Nome do vendedor', 'Nome da filial', 'Nome da rede']).size().reset_index(name='Quantidade')
    ranking_df['Ranking'] = ranking_df['Quantidade'].rank(method='first', ascending=False).astype(int)
    ranking_df = ranking_df.sort_values(by='Ranking')
    ranking_df = ranking_df[['Ranking', 'Nome do vendedor', 'Nome da filial', 'Nome da rede', 'Quantidade']]

    top_vendedores_data = ranking_df.to_dict('records')
    top_vendedores_columns = [{'name': col, 'id': col} for col in ranking_df.columns]

    top_dispositivos_df = df['Descrição'].value_counts().nlargest(10).reset_index()
    top_dispositivos_df.columns = ['Descrição', 'Quantidade']

    fig_dispositivos = px.bar(
        top_dispositivos_df,
        x='Descrição',
        y='Quantidade',
        text='Quantidade'
    )
    fig_dispositivos.update_traces(textposition='outside')
    fig_dispositivos.update_layout(template='plotly_dark', title='Top 10 Dispositivos Mais Avaliados')

    return kpis, fig_gerados, fig_utilizados, fig_ticket, top_vendedores_data, top_vendedores_columns, fig_dispositivos

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
