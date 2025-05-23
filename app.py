import os
import base64
import io
import pandas as pd
import dash
from dash import Dash, html, dcc, Input, Output, State, callback_context, dash_table, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
from unidecode import unidecode
from datetime import datetime

# Inicializa o app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Layout
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
    html.Div(id='filtros', style={'marginTop': '20px'}),
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'}),
])

# Callback principal
@app.callback(
    Output('filtros', 'children'),
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('ranking-vendedores', 'children'),
    Output('error-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def processar_arquivo(contents, filename):
    if contents is None:
        return no_update, no_update, no_update, no_update, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        # Normaliza colunas
        df.columns = [unidecode(c).strip().lower() for c in df.columns]

        # Colunas obrigatórias
        obrigatorias = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher', 'nome do vendedor', 'nome da filial', 'nome da rede']
        for col in obrigatorias:
            if col not in df.columns:
                return no_update, no_update, no_update, no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        # Conversão de data
        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes'] = df['criado em'].dt.strftime('%B').str.capitalize()

        # Salva DataFrame no dcc.Store
        filtros = dbc.Row([
            dbc.Col(dcc.Dropdown(options=[{'label': m, 'value': m} for m in sorted(df['mes'].dropna().unique())],
                                 multi=True, placeholder="Mês", id='filtro-mes'), md=4),
            dbc.Col(dcc.Dropdown(options=[{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())],
                                 multi=True, placeholder="Rede", id='filtro-rede'), md=4),
            dbc.Col(dcc.Dropdown(options=[{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())],
                                 multi=True, placeholder="Situação do voucher", id='filtro-situacao'), md=4),
        ])

        # Armazena temporariamente o DataFrame no servidor (pouco escalável, mas funcional para uso leve)
        app.df = df

        return filtros, no_update, no_update, no_update, ""

    except Exception as e:
        return no_update, no_update, no_update, no_update, f"Erro ao processar arquivo: {str(e)}"

# Callback de atualização com filtros
@app.callback(
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('ranking-vendedores', 'children'),
    Input('filtro-mes', 'value'),
    Input('filtro-rede', 'value'),
    Input('filtro-situacao', 'value'),
)
def atualizar_dashboard(mes, rede, situacao):
    try:
        df = app.df.copy()

        # Aplica filtros
        if mes:
            df = df[df['mes'].isin(mes)]
        if rede:
            df = df[df['nome da rede'].isin(rede)]
        if situacao:
            df = df[df['situacao do voucher'].isin(situacao)]

        total_gerados = len(df)
        dispositivos = df['imei'].nunique()
        captacao = df['valor do voucher'].sum()
        ticket = captacao / dispositivos if dispositivos > 0 else 0

        utilizados = df[df['situacao do voucher'].str.lower() == 'utilizado']
        conversao = len(utilizados) / total_gerados * 100 if total_gerados > 0 else 0

        kpis = dbc.Row([
            dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(f"{total_gerados}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(f"{dispositivos}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("🎫 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")], body=True, color="dark", inverse=True), md=2),
        ])

        fig_gerados = px.line(df.groupby(df['criado em'].dt.date).size().reset_index(name='Qtd'),
                              x='criado em', y='Qtd', title="📅 Vouchers Gerados por Dia")

        fig_utilizados = px.line(utilizados.groupby(utilizados['criado em'].dt.date).size().reset_index(name='Qtd'),
                                 x='criado em', y='Qtd', title="📅 Vouchers Utilizados por Dia")

        fig_ticket = px.line(utilizados.groupby(utilizados['criado em'].dt.date)['valor do voucher'].mean().reset_index(name='Média'),
                             x='criado em', y='Média', title="💸 Ticket Médio Diário")

        graficos = dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
            dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
            dbc.Col(dcc.Graph(figure=fig_ticket), md=4),
        ])

        # Ranking de vendedores (apenas vouchers utilizados)
        ranking = utilizados.groupby(['nome do vendedor', 'nome da filial', 'nome da rede']) \
            .size().reset_index(name='Qtd').sort_values(by='Qtd', ascending=False).head(10)

        tabela = dash_table.DataTable(
            columns=[
                {"name": "nome do vendedor", "id": "nome do vendedor"},
                {"name": "nome da filial", "id": "nome da filial"},
                {"name": "nome da rede", "id": "nome da rede"},
                {"name": "Qtd", "id": "Qtd"}
            ],
            data=ranking.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_header={'fontWeight': 'bold', 'backgroundColor': 'black', 'color': 'white'},
            style_cell={'textAlign': 'left'},
        )

        return kpis, graficos, html.Div([
            html.H5("🏆 Top 10 Vendedores por Volume de Vouchers", style={'marginTop': '20px'}),
            tabela
        ])

    except Exception as e:
        return no_update, no_update, no_update

# Executa o app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
