import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
from unidecode import unidecode
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={"textAlign": "center"}),

    dcc.Upload(
        id='upload-data',
        children=html.Div([
            "📁 Arraste ou selecione o arquivo .xlsx"
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '2px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),

    html.Div(id='erro-upload', style={'color': 'red', 'textAlign': 'center'}),

    dcc.Store(id='filtered-data'),

    html.Div([
        dcc.Dropdown(id='month-filter', placeholder='Mês'),
        dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'),
        dcc.Dropdown(id='situacao-filter', placeholder='Situação do voucher')
    ], style={'display': 'flex', 'gap': '10px', 'margin': '10px'}),

    html.Div(id='kpi-cards', style={'display': 'flex', 'gap': '20px', 'margin': '20px'}),

    html.Div([
        dcc.Graph(id='grafico-gerados'),
        dcc.Graph(id='grafico-utilizados'),
        dcc.Graph(id='grafico-ticket')
    ], style={'display': 'flex', 'gap': '10px'}),

    html.Hr(),

    html.H4("Ranking de Vendedores"),
    dash_table.DataTable(id='tabela-vendedores'),

    html.Hr(),

    html.H4("Top Dispositivos"),
    dcc.Graph(id='grafico-top-dispositivos'),
])

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'xlsx' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
            df.columns = [unidecode(str(col)).strip() for col in df.columns]
            return df
        else:
            return None
    except Exception as e:
        print(e)
        return None

@app.callback(
    Output('filtered-data', 'data'),
    Output('month-filter', 'options'),
    Output('month-filter', 'value'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('erro-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    allow_duplicate=True,
    prevent_initial_call=True
)
def atualizar_filtros(contents, filename):
    if contents is None:
        return dash.no_update, [], None, [], "", "Arquivo não carregado."

    df = parse_contents(contents, filename)
    if df is None:
        return dash.no_update, [], None, [], "", "Erro ao ler arquivo."

    if 'Criado em' not in df.columns:
        return dash.no_update, [], None, [], "", "Coluna 'Criado em' não encontrada."

    try:
        df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
        df = df.dropna(subset=['Criado em'])
        df['mes'] = df['Criado em'].dt.strftime('%B')

        meses = sorted(df['mes'].dropna().unique(), key=lambda x: datetime.strptime(x, "%B").month)
        redes = df['Nome da rede'].dropna().unique()
        situacoes = df['Situacao do voucher'].dropna().unique()

        return (
            df.to_dict('records'),
            [{'label': m, 'value': m} for m in meses],
            meses[-1],
            [{'label': r, 'value': r} for r in redes],
            [{'label': s, 'value': s} for s in situacoes],
            ""
        )
    except Exception as e:
        return dash.no_update, [], None, [], "", f"Erro ao processar: {str(e)}"

@app.callback(
    Output('kpi-cards', 'children'),
    Output('grafico-gerados', 'figure'),
    Output('grafico-utilizados', 'figure'),
    Output('grafico-ticket', 'figure'),
    Output('tabela-vendedores', 'data'),
    Output('tabela-vendedores', 'columns'),
    Output('grafico-top-dispositivos', 'figure'),
    Input('filtered-data', 'data'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value'),
    allow_duplicate=True,
    prevent_initial_call=True
)
def atualizar_dashboard(data, mes, rede, situacao):
    if not data:
        return [], {}, {}, {}, [], [], {}

    df = pd.DataFrame(data)
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df.dropna(subset=['Criado em'])
    df['mes'] = df['Criado em'].dt.strftime('%B')

    if mes:
        df = df[df['mes'] == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacao:
        df = df[df['Situacao do voucher'] == situacao]

    kpis = [
        dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(df['Imel'].nunique())], color="dark", body=True),
        dbc.Card([html.H5("💰 Captação Total"), html.H3("R$ {:,.2f}".format(df['Valor do voucher'].sum()))], color="dark", body=True),
        dbc.Card([html.H5("📊 Ticket Médio"), html.H3("R$ {:,.2f}".format(df['Valor do voucher'].mean()))], color="dark", body=True),
        dbc.Card([html.H5("📈 Conversão"), html.H3("{:.2f}%".format(100 * df[df['Situacao do voucher'] == 'UTILIZADO']['Imel'].count() / df['Imel'].count() if df['Imel'].count() > 0 else 0))], color="dark", body=True),
    ]

    fig1 = px.line(df.groupby('Criado em').size().reset_index(name='Qtd'), x='Criado em', y='Qtd', title='Vouchers Gerados por Dia')
    fig2 = px.line(df[df['Situacao do voucher'] == 'UTILIZADO'].groupby('Criado em').size().reset_index(name='Qtd'), x='Criado em', y='Qtd', title='Vouchers Utilizados por Dia')
    fig3 = px.line(df.groupby('Criado em')['Valor do voucher'].mean().reset_index(), x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

    ranking = df[df['Situacao do voucher'] == 'UTILIZADO'].groupby(['Nome do vendedor', 'Nome da filial']).size().reset_index(name='Qtd')
    ranking['Ranking'] = ranking['Qtd'].rank(method='dense', ascending=False).astype(int)
    ranking = ranking.sort_values('Ranking')
    ranking = ranking[['Ranking', 'Nome do vendedor', 'Nome da filial']]

    top_dispositivos = df['Descricao'].value_counts().nlargest(10).reset_index()
    top_dispositivos.columns = ['Descrição', 'Quantidade']
    fig_top = px.bar(top_dispositivos, x='Descrição', y='Quantidade', title='Top Dispositivos')

    return (
        kpis,
        fig1,
        fig2,
        fig3,
        ranking.to_dict('records'),
        [{"name": i, "id": i} for i in ranking.columns],
        fig_top
    )

import os

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))



