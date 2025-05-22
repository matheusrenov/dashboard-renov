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

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={'textAlign': 'center'}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center'
        },
        multiple=False
    ),

    html.Div(id='error-upload', style={'color': 'red', 'textAlign': 'center', 'marginTop': 10}),

    html.Div([
        dbc.Row([
            dbc.Col(dcc.Dropdown(id='filtro-mes', multi=True, placeholder='📆 Mês'), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-rede', multi=True, placeholder='🏬 Nome da rede'), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-situacao', multi=True, placeholder='📄 Situação'), md=4),
        ], style={'marginTop': 20}),
    ], id='filtros-area'),

    html.Div(id='kpi-cards', style={'marginTop': 20}),
    html.Div(id='graficos', style={'marginTop': 30}),
    html.Div(id='ranking-vendedores', style={'marginTop': 30}),
])

@app.callback(
    Output('filtro-mes', 'options'),
    Output('filtro-rede', 'options'),
    Output('filtro-situacao', 'options'),
    Output('filtro-mes', 'value'),
    Output('filtro-rede', 'value'),
    Output('filtro-situacao', 'value'),
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('ranking-vendedores', 'children'),
    Output('error-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def carregar_arquivo(contents, filename):
    if contents is None:
        return [[], [], [], None, None, None, dash.no_update, dash.no_update, dash.no_update, ""]
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        # Normalize columns
        df.columns = [unidecode(c).strip().lower().replace("  ", " ") for c in df.columns]

        required = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher', 'nome do rede', 'nome do vendedor']
        for col in required:
            if col not in df.columns:
                return [[], [], [], None, None, None, dash.no_update, dash.no_update, dash.no_update,
                        f"❌ Coluna obrigatória não encontrada: {col}"]

        # Ensure datetime
        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df = df.dropna(subset=['criado em'])

        # Add month
        df['mes'] = df['criado em'].dt.strftime('%b')

        mes_options = [{'label': m, 'value': m} for m in sorted(df['mes'].dropna().unique())]
        rede_options = [{'label': r, 'value': r} for r in sorted(df['nome do rede'].dropna().unique())]
        situ_options = [{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())]

        return mes_options, rede_options, situ_options, [], [], [], dash.no_update, dash.no_update, dash.no_update, ""

    except Exception as e:
        return [[], [], [], None, None, None, dash.no_update, dash.no_update, dash.no_update,
                f"Erro ao processar arquivo: {str(e)}"]
@app.callback(
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('ranking-vendedores', 'children'),
    Output('error-upload', 'children'),
    Input('filtro-mes', 'value'),
    Input('filtro-rede', 'value'),
    Input('filtro-situacao', 'value'),
    State('upload-data', 'contents')
)
def atualizar_dashboard(meses, redes, situacoes, contents):
    if contents is None:
        return dash.no_update, dash.no_update, dash.no_update, ""

    try:
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        df.columns = [unidecode(c).strip().lower() for c in df.columns]

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df = df.dropna(subset=['criado em'])
        df['mes'] = df['criado em'].dt.strftime('%b')

        # Filtros
        if meses:
            df = df[df['mes'].isin(meses)]
        if redes:
            df = df[df['nome do rede'].isin(redes)]
        if situacoes:
            df = df[df['situacao do voucher'].isin(situacoes)]

        total_gerados = df.shape[0]
        dispositivos = df['imei'].nunique()
        captacao = df['valor do voucher'].sum()
        ticket = captacao / dispositivos if dispositivos else 0
        usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
        conversao = (len(usados) / total_gerados * 100) if total_gerados else 0

        kpis = dbc.Row([
            dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(f"{total_gerados}")],
                             body=True, color="dark", inverse=True), md=3),
            dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(f"{dispositivos}")],
                             body=True, color="dark", inverse=True), md=3),
            dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")],
                             body=True, color="dark", inverse=True), md=3),
            dbc.Col(dbc.Card([html.H5("🎯 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")],
                             body=True, color="dark", inverse=True), md=3),
            dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")],
                             body=True, color="dark", inverse=True), md=3),
        ], className="mb-4")

        fig_gerados = px.line(
            df.groupby(df['criado em'].dt.date).size().reset_index(name='Qtd'),
            x='criado em', y='Qtd', title="📆 Vouchers Gerados por Dia"
        )

        fig_utilizados = px.line(
            usados.groupby(usados['criado em'].dt.date).size().reset_index(name='Qtd'),
            x='criado em', y='Qtd', title="📆 Vouchers Utilizados por Dia"
        )

        fig_ticket = px.line(
            usados.groupby(usados['criado em'].dt.date)['valor do voucher']
            .mean().reset_index(name='Média'),
            x='criado em', y='Média', title="🎫 Ticket Médio Diário"
        )

        graficos = dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
            dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
            dbc.Col(dcc.Graph(figure=fig_ticket), md=4),
        ])

        # Ranking Vendedores
        ranking = df.groupby(['nome do vendedor', 'nome do filial'])['valor do voucher'].sum().reset_index()
        ranking['valor do voucher'] = ranking['valor do voucher'].round(2)
        ranking = ranking.sort_values(by='valor do voucher', ascending=False).head(20)
        ranking.insert(0, 'Ranking', range(1, 1 + len(ranking)))

        ranking_table = dash_table.DataTable(
            columns=[{'name': i.title(), 'id': i} for i in ranking.columns],
            data=ranking.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            page_size=20,
        )

        return kpis, graficos, ranking_table, ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar: {str(e)}"
# Layout completo agora com filtros e ranking de vendedores
app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={'textAlign': 'center'}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center'
        },
        multiple=False
    ),
    html.Div(id='error-upload', style={'color': 'red', 'textAlign': 'center', 'marginTop': 10}),
    
    dbc.Row([
        dbc.Col(dcc.Dropdown(id='filtro-mes', multi=True, placeholder='🗓️ Mês'), md=4),
        dbc.Col(dcc.Dropdown(id='filtro-rede', multi=True, placeholder='🌐 Nome da Rede'), md=4),
        dbc.Col(dcc.Dropdown(id='filtro-situacao', multi=True, placeholder='📄 Situação do Voucher'), md=4),
    ], style={'marginTop': 20}),

    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '40px'}),
])

# Callback de atualização dos filtros com base no arquivo
@app.callback(
    Output('filtro-mes', 'options'),
    Output('filtro-rede', 'options'),
    Output('filtro-situacao', 'options'),
    Input('upload-data', 'contents')
)
def atualizar_filtros(contents):
    if contents is None:
        return [], [], []

    try:
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        df.columns = [unidecode(c).strip().lower() for c in df.columns]
        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes'] = df['criado em'].dt.strftime('%b')

        return (
            [{'label': m, 'value': m} for m in sorted(df['mes'].dropna().unique())],
            [{'label': r, 'value': r} for r in sorted(df['nome do rede'].dropna().unique())],
            [{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())],
        )
    except Exception:
        return [], [], []

# 🔥 Inicialização segura
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
