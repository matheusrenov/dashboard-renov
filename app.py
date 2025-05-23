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

# 🚀 Inicialização do app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# 🧠 Layout principal
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
    html.Div(id='filtros', style={'marginTop': 20}),
    html.Div(id='kpi-cards', style={'marginTop': 20}),
    html.Div(id='graficos', style={'marginTop': 20}),
    html.Div(id='ranking-vendedores', style={'marginTop': 20})
])

# ♻️ Filtro dinâmico
@app.callback(
    Output('filtros', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def atualizar_filtros(contents, filename):
    if contents is None:
        return ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        df.columns = [unidecode(col).strip().lower() for col in df.columns]

        filtros = dbc.Row([
            dbc.Col(dcc.Dropdown(
                id='filtro-mes',
                options=[{'label': m, 'value': m} for m in sorted(df['criado em'].dt.strftime('%B').unique())],
                placeholder='Mês',
                multi=True
            ), md=4),
            dbc.Col(dcc.Dropdown(
                id='filtro-rede',
                options=[{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())],
                placeholder='Rede',
                multi=True
            ), md=4),
            dbc.Col(dcc.Dropdown(
                id='filtro-situacao',
                options=[{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())],
                placeholder='Situação do voucher',
                multi=True
            ), md=4)
        ])
        return filtros
    except Exception as e:
        return f"Erro ao carregar filtros: {str(e)}"

# 🎯 Dashboard completo com filtros
@app.callback(
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('ranking-vendedores', 'children'),
    Output('error-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    Input('filtro-mes', 'value'),
    Input('filtro-rede', 'value'),
    Input('filtro-situacao', 'value')
)
def atualizar_dashboard(contents, filename, meses, redes, situacoes):
    if contents is None:
        return dash.no_update, dash.no_update, dash.no_update, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        df.columns = [unidecode(col).strip().lower() for col in df.columns]
        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df = df.dropna(subset=['criado em'])

        # Filtros aplicados
        if meses:
            df = df[df['criado em'].dt.strftime('%B').isin(meses)]
        if redes:
            df = df[df['nome da rede'].isin(redes)]
        if situacoes:
            df = df[df['situacao do voucher'].isin(situacoes)]

        # KPIs
        total = df.shape[0]
        dispositivos = df['imei'].nunique()
        captacao = df['valor do voucher'].sum()
        ticket = captacao / dispositivos if dispositivos else 0
        usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
        conversao = len(usados) / total * 100 if total else 0

        kpis = dbc.Row([
            dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(f"{total}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(f"{dispositivos}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("🎫 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")], body=True, color="dark", inverse=True), md=2)
        ])

        # Gráficos
        df['data'] = df['criado em'].dt.date
        fig_gerados = px.line(df.groupby('data').size().reset_index(name='Qtd'), x='data', y='Qtd', title="📆 Vouchers Gerados por Dia")

        usados['data'] = usados['criado em'].dt.date
        fig_utilizados = px.line(usados.groupby('data').size().reset_index(name='Qtd'), x='data', y='Qtd', title="📆 Vouchers Utilizados por Dia")

        fig_ticket = px.line(usados.groupby('data')['valor do voucher'].mean().reset_index(name='Média'), x='data', y='Média', title="🎫 Ticket Médio Diário")

        graficos = dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
            dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
            dbc.Col(dcc.Graph(figure=fig_ticket), md=4),
        ])

        # Ranking
        ranking = usados.groupby(['nome do vendedor', 'nome da filial', 'nome da rede']).size().reset_index(name='Qtd')
        ranking = ranking.sort_values(by='Qtd', ascending=False).head(10)

        tabela = dash_table.DataTable(
            columns=[
                {"name": col, "id": col} for col in ranking.columns
            ],
            data=ranking.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'black', 'color': 'white'},
            style_cell={'textAlign': 'left'},
        )

        return kpis, graficos, html.Div([
            html.H5("🏆 Top 10 Vendedores por Volume de Vouchers"),
            tabela
        ]), ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar arquivo: {str(e)}"

# 🚀 Execução
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
