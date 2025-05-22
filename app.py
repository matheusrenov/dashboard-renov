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

# Layout principal
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
            dbc.Col(dcc.Dropdown(id='filtro-mes', multi=True, placeholder="Mês"), md=3),
            dbc.Col(dcc.Dropdown(id='filtro-rede', multi=True, placeholder="Nome da rede"), md=3),
            dbc.Col(dcc.Dropdown(id='filtro-situacao', multi=True, placeholder="Situação do voucher"), md=3),
        ], style={"marginTop": 10})
    ]),
    
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'}),
])
from dash.exceptions import PreventUpdate

# Callback principal com múltiplas saídas
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
    State('upload-data', 'filename'),
    prevent_initial_call='initial_duplicate_check',
    allow_duplicate=True
)
def processar_arquivo(contents, filename):
    if contents is None:
        raise PreventUpdate

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        df.columns = [unidecode(c).strip().lower() for c in df.columns]

        obrigatorias = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher', 'nome do vendedor']
        for col in obrigatorias:
            if col not in df.columns:
                return [dash.no_update] * 9 + [f"❌ Coluna obrigatória não encontrada: {col}"]

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df = df.dropna(subset=['criado em'])
        df['mes'] = df['criado em'].dt.strftime('%b')

        total_gerados = len(df)
        dispositivos = df['imei'].nunique()
        captacao = df['valor do voucher'].sum()
        ticket = captacao / dispositivos if dispositivos else 0

        usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
        conversao = len(usados) / total_gerados * 100 if total_gerados else 0

        kpis = dbc.Row([
            dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(total_gerados)], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(dispositivos)], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("🎯 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")], body=True, color="dark", inverse=True), md=2),
        ])

        fig_gerados = px.line(df.groupby(df['criado em'].dt.date).size().reset_index(name='Qtd'), x='criado em', y='Qtd', title="📆 Vouchers Gerados por Dia")
        fig_utilizados = px.line(usados.groupby(usados['criado em'].dt.date).size().reset_index(name='Qtd'), x='criado em', y='Qtd', title="📆 Vouchers Utilizados por Dia")
        fig_ticket = px.line(usados.groupby(usados['criado em'].dt.date)['valor do voucher'].mean().reset_index(name='Média'), x='criado em', y='Média', title="🎫 Ticket Médio Diário")

        graficos = dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
            dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
            dbc.Col(dcc.Graph(figure=fig_ticket), md=4),
        ])

        ranking_df = df.groupby('nome do vendedor').size().reset_index(name='Qtd').sort_values(by='Qtd', ascending=False).head(10)
        tabela = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ranking_df.columns],
            data=ranking_df.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'black', 'color': 'white'}
        )

        ranking = html.Div([
            html.H5("🏆 Top 10 Vendedores por Volume de Vouchers"),
            tabela
        ])

        opcoes_mes = [{'label': m, 'value': m} for m in sorted(df['mes'].dropna().unique())]
        opcoes_rede = [{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())] if 'nome da rede' in df.columns else []
        opcoes_situacao = [{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())]

        return (
            opcoes_mes, opcoes_rede, opcoes_situacao,
            [], [], [],
            kpis, graficos, ranking, ""
        )

    except Exception as e:
        return [dash.no_update] * 9 + [f"Erro ao processar arquivo: {str(e)}"]
# 🚀 Inicialização segura com debug e porta
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
