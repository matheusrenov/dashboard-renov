import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
from unidecode import unidecode
from datetime import datetime

# Inicialização
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Layout
app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={'textAlign': 'center'}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={'width': '100%', 'height': '60px', 'lineHeight': '60px',
               'borderWidth': '1px', 'borderStyle': 'dashed',
               'borderRadius': '5px', 'textAlign': 'center'},
        multiple=False
    ),

    html.Div(id='error-upload', style={'color': 'red', 'textAlign': 'center', 'marginTop': 10}),
    html.Div(id='filtros-container'),
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'}),
    dcc.Store(id='dados-filtrados')
])

# Callback processamento inicial
@app.callback(
    Output('filtros-container', 'children'),
    Output('dados-filtrados', 'data'),
    Output('error-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def processar_arquivo(contents, filename):
    if contents is None:
        return dash.no_update, dash.no_update, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        df.columns = [unidecode(c).strip().lower() for c in df.columns]
        colunas_obrigatorias = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher',
                                'nome do vendedor', 'nome da filial', 'nome da rede']

        for col in colunas_obrigatorias:
            if col not in df.columns:
                return dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df = df.dropna(subset=['criado em'])

        filtros = dbc.Row([
            dbc.Col(dcc.Dropdown(
                id='filtro-mes',
                options=[{'label': mes, 'value': mes} for mes in sorted(df['criado em'].dt.strftime('%b').unique())],
                multi=True,
                placeholder="Mês"
            ), md=4),
            dbc.Col(dcc.Dropdown(
                id='filtro-rede',
                options=[{'label': rede, 'value': rede} for rede in sorted(df['nome da rede'].dropna().unique())],
                multi=True,
                placeholder="Rede"
            ), md=4),
            dbc.Col(dcc.Dropdown(
                id='filtro-situacao',
                options=[{'label': sit, 'value': sit} for sit in sorted(df['situacao do voucher'].dropna().unique())],
                multi=True,
                placeholder="Situação do voucher"
            ), md=4)
        ], style={'marginTop': '20px'})

        return filtros, df.to_dict('records'), ""

    except Exception as e:
        return dash.no_update, dash.no_update, f"Erro ao processar arquivo: {str(e)}"

# Atualiza dashboard conforme filtros
@app.callback(
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('ranking-vendedores', 'children'),
    Input('filtro-mes', 'value'),
    Input('filtro-rede', 'value'),
    Input('filtro-situacao', 'value'),
    State('dados-filtrados', 'data')
)
def atualizar_dashboard(filtro_mes, filtro_rede, filtro_situacao, data):
    if data is None:
        return dash.no_update, dash.no_update, dash.no_update

    df = pd.DataFrame(data)
    df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
    df = df.dropna(subset=['criado em'])

    # Aplicar filtros
    if filtro_mes:
        df = df[df['criado em'].dt.strftime('%b').isin(filtro_mes)]
    if filtro_rede:
        df = df[df['nome da rede'].isin(filtro_rede)]
    if filtro_situacao:
        df = df[df['situacao do voucher'].isin(filtro_situacao)]

    total_gerados = len(df)
    dispositivos = df['imei'].nunique()
    captacao = df['valor do voucher'].sum()
    ticket = captacao / dispositivos if dispositivos > 0 else 0
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    conversao = len(usados) / total_gerados * 100 if total_gerados > 0 else 0

    kpis = dbc.Row([
        dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(f"{total_gerados}")], body=True,
                         color="dark", inverse=True), md=2),
        dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(f"{dispositivos}")], body=True,
                         color="dark", inverse=True), md=2),
        dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")], body=True,
                         color="dark", inverse=True), md=2),
        dbc.Col(dbc.Card([html.H5("🎯 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")], body=True,
                         color="dark", inverse=True), md=2),
        dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")], body=True,
                         color="dark", inverse=True), md=2),
    ], justify="center")

    fig_gerados = px.line(df.groupby(df['criado em'].dt.date).size().reset_index(name='Qtd'),
                          x='criado em', y='Qtd', title="📅 Vouchers Gerados por Dia")

    fig_utilizados = px.line(usados.groupby(usados['criado em'].dt.date).size().reset_index(name='Qtd'),
                             x='criado em', y='Qtd', title="📅 Vouchers Utilizados por Dia")

    fig_ticket = px.line(usados.groupby(usados['criado em'].dt.date)['valor do voucher'].mean().reset_index(name='Média'),
                         x='criado em', y='Média', title="🎫 Ticket Médio Diário")

    graficos = dbc.Row([
        dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
        dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
        dbc.Col(dcc.Graph(figure=fig_ticket), md=4),
    ])

    ranking_df = usados.groupby(['nome do vendedor', 'nome da filial', 'nome da rede']).size().reset_index(name='Qtd')
    ranking_df = ranking_df.sort_values(by='Qtd', ascending=False).head(10)

    tabela = html.Div([
        html.H5("🏆 Top 10 Vendedores por Volume de Vouchers"),
        dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ranking_df.columns],
            data=ranking_df.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'whiteSpace': 'normal'},
            style_header={'fontWeight': 'bold', 'backgroundColor': 'black', 'color': 'white'}
        )
    ])

    return kpis, graficos, tabela

# Start seguro
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
