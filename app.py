import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import io
import base64
import os
from datetime import datetime

# Inicialização do app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Layout principal
app.layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        dbc.Col(html.H1("Dashboard de Resultados", style={"color": "black"}), md=10),
        dbc.Col(html.Img(src="https://i.ibb.co/7kkVP9g/logo-renov.png", height="50px"), md=2, style={"textAlign": "right"})
    ], className="my-3"),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📂 Arraste ou selecione o arquivo .xlsx']),
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
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do voucher', multi=True), md=4)
    ], className="mb-4"),

    dbc.Row(id='kpi-container', className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dash_table.DataTable(id='ranking-vendedores',
                                     style_cell={'fontSize': 11, 'textAlign': 'left', 'whiteSpace': 'normal'},
                                     style_table={'overflowX': 'auto'},
                                     style_header={'backgroundColor': '#e8e8e8', 'fontWeight': 'bold'}), md=12)
    ], className="mb-4"),

    dcc.Store(id='raw-data'),
    dcc.Store(id='hidden-data'),
    dcc.Store(id='filtered-data')
])

# Função para processar o upload
def process_data(contents):
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        df.columns = df.columns.str.strip()
        df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
        df = df[df['Criado em'].notna()]

        # Nome do mês em português
        mes_map = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        df['Mês'] = df['Criado em'].dt.month.map(mes_map)
        return df
    except Exception as e:
        print(f"Erro ao processar: {e}")
        return None

# Callback para carregar o arquivo
@app.callback(
    Output('raw-data', 'data'),
    Input('upload-data', 'contents')
)
def carregar_dados(contents):
    if contents is None:
        return dash.no_update
    df = process_data(contents)
    return df.to_json(date_format='iso', orient='split') if df is not None else None

# Atualizar filtros com base no arquivo
@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('month-filter', 'value'),
    Output('filtered-data', 'data'),
    Input('hidden-data', 'data')
)
def atualizar_filtros(json_data):
    if json_data is None:
        return [], [], [], None, None

    df = pd.read_json(io.StringIO(json_data), orient='split')

    ordem_meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    meses = sorted(df['Mês'].dropna().unique(), key=lambda x: ordem_meses.index(x), reverse=True)
    redes = sorted(df['Nome da rede'].dropna().unique())
    situacoes = sorted(df['Situacao do voucher'].dropna().unique())

    mes_recente = df['Criado em'].max().month
    nome_mes = ordem_meses[mes_recente - 1]
    df_filtrado = df[df['Mês'] == nome_mes]

    return (
        [{'label': m, 'value': m} for m in meses],
        [{'label': r, 'value': r} for r in redes],
        [{'label': s, 'value': s} for s in situacoes],
        nome_mes,
        df_filtrado.to_json(date_format='iso', orient='split')
    )


# Callback principal
@app.callback(
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Output('ranking-vendedores', 'data'),
    Output('ranking-vendedores', 'columns'),
    Input('filtered-data', 'data')
)
def atualizar_dashboard(json_data):
    if json_data is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, [], []

    df = pd.read_json(io.StringIO(json_data), orient='split')
    utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']

    total = len(df)
    total_utilizados = len(utilizados)
    valor_total = utilizados['Valor do voucher'].sum()
    ticket_medio = utilizados['Valor do voucher'].mean()
    conversao = (total_utilizados / total * 100) if total else 0

    kpis = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("📦 Dispositivos Captados"), html.H2(f"{total_utilizados}")]), className="shadow"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("💰 Captação Total"), html.H2(f"R$ {valor_total:,.2f}")]), className="shadow"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("📊 Ticket Médio"), html.H2(f"R$ {ticket_medio:,.2f}")]), className="shadow"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("📈 Conversão"), html.H2(f"{conversao:.2f}%")]), className="shadow"), md=3)
    ])

    fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(utilizados, x='Criado em', title='Vouchers Utilizados por Dia')
    fig_ticket = px.line(utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(),
                         x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

    # Ranking de vendedores
    ranking = utilizados.groupby(['Nome do vendedor', 'Nome da filial', 'Nome da rede']) \
        .size().reset_index(name='Quantidade')
    ranking = ranking.sort_values(by='Quantidade', ascending=False).reset_index(drop=True)
    ranking.insert(0, 'Ranking', ranking.index + 1)
    data = ranking.to_dict('records')
    columns = [{'name': col, 'id': col} for col in ranking.columns]

    return kpis, fig_gerados, fig_utilizados, fig_ticket, data, columns

# Run
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
