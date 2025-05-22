import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table
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
            dbc.Col(dcc.Dropdown(id='filtro-mes', multi=True, placeholder="Mês"), md=3),
            dbc.Col(dcc.Dropdown(id='filtro-rede', multi=True, placeholder="Nome da rede"), md=3),
            dbc.Col(dcc.Dropdown(id='filtro-situacao', multi=True, placeholder="Situação"), md=3),
        ], style={'marginTop': 20}),
    ], id='filtros-container', style={'display': 'none'}),

    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'})
])

def normalizar_colunas(df):
    df.columns = [unidecode(c).strip().lower() for c in df.columns]
    return df

@app.callback(
    Output('filtro-mes', 'options'),
    Output('filtro-rede', 'options'),
    Output('filtro-situacao', 'options'),
    Output('filtros-container', 'style'),
    Output('error-upload', 'children'),
    Output('filtro-mes', 'value'),
    Output('filtro-rede', 'value'),
    Output('filtro-situacao', 'value'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def carregar_e_configurar_filtros(contents, filename):
    if contents is None:
        return [], [], [], {'display': 'none'}, "", None, None, None

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        df = normalizar_colunas(df)

        print("📄 Colunas encontradas:", df.columns.tolist())

        colunas_esperadas = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher', 'nome da rede', 'nome do vendedor']
        for col in colunas_esperadas:
            if col not in df.columns:
                return [], [], [], {'display': 'none'}, f"❌ Coluna obrigatória não encontrada: {col}", None, None, None

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes'] = df['criado em'].dt.strftime('%b')

        mes_op = [{'label': m, 'value': m} for m in sorted(df['mes'].dropna().unique())]
        rede_op = [{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())]
        sit_op = [{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())]

        return mes_op, rede_op, sit_op, {'display': 'block'}, "", None, None, None

    except Exception as e:
        return [], [], [], {'display': 'none'}, f"Erro ao processar arquivo: {str(e)}", None, None, None

# Callback para atualizar dados após filtros
@app.callback(
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('ranking-vendedores', 'children'),
    Output('error-upload', 'children'),
    Input('upload-data', 'contents'),
    Input('filtro-mes', 'value'),
    Input('filtro-rede', 'value'),
    Input('filtro-situacao', 'value'),
    State('upload-data', 'filename'),
)
def atualizar_dashboard(contents, mes, rede, situacao, filename):
    if contents is None:
        return "", "", "", ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        df = normalizar_colunas(df)

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes'] = df['criado em'].dt.strftime('%b')

        if mes: df = df[df['mes'].isin(mes)]
        if rede: df = df[df['nome da rede'].isin(rede)]
        if situacao: df = df[df['situacao do voucher'].isin(situacao)]

        total_gerados = df.shape[0]
        dispositivos = df['imei'].nunique()
        captacao = df['valor do voucher'].sum()
        ticket = captacao / dispositivos if dispositivos > 0 else 0
        usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
        conversao = len(usados) / total_gerados * 100 if total_gerados > 0 else 0

        kpis = dbc.Row([
            dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(f"{total_gerados}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(f"{dispositivos}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("🎯 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")], body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")], body=True, color="dark", inverse=True), md=2),
        ])

        grafico1 = px.line(df.groupby(df['criado em'].dt.date).size().reset_index(name='Qtd'), x='criado em', y='Qtd', title="📅 Vouchers Gerados por Dia")
        grafico2 = px.line(usados.groupby(usados['criado em'].dt.date).size().reset_index(name='Qtd'), x='criado em', y='Qtd', title="📅 Vouchers Utilizados por Dia")
        grafico3 = px.line(usados.groupby(usados['criado em'].dt.date)['valor do voucher'].mean().reset_index(name='Média'), x='criado em', y='Média', title="🎫 Ticket Médio Diário")

        graficos = dbc.Row([
            dbc.Col(dcc.Graph(figure=grafico1), md=4),
            dbc.Col(dcc.Graph(figure=grafico2), md=4),
            dbc.Col(dcc.Graph(figure=grafico3), md=4),
        ])

        ranking = df.groupby('nome do vendedor').size().reset_index(name='Quantidade').sort_values(by='Quantidade', ascending=False)
        ranking_component = dash_table.DataTable(
            columns=[{'name': i, 'id': i} for i in ranking.columns],
            data=ranking.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
        )

        return kpis, graficos, ranking_component, ""

    except Exception as e:
        return "", "", "", f"Erro ao processar arquivo: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
