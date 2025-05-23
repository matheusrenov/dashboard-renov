import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
from unidecode import unidecode
from datetime import datetime

# 🧠 App
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# 🧱 Layout
app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={'textAlign': 'center'}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={
            'width': '100%', 'height': '60px',
            'lineHeight': '60px', 'borderWidth': '1px',
            'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center'
        },
        multiple=False
    ),

    html.Div(id='error-upload', style={'color': 'red', 'textAlign': 'center', 'marginTop': 10}),

    html.Div(id='filtros', style={'marginTop': '20px'}),
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'}),
])

# 🔁 Atualização layout completo após upload
@app.callback(
    Output('filtros', 'children'),
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('ranking-vendedores', 'children'),
    Output('error-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def atualizar_dashboard(contents, filename):
    if contents is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        # 🧹 Normalização
        df.columns = [unidecode(c).strip().lower() for c in df.columns]

        # ✅ Validação
        colunas_requeridas = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher',
                              'nome do vendedor', 'nome da filial', 'nome da rede']
        for col in colunas_requeridas:
            if col not in df.columns:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df.dropna(subset=['criado em'], inplace=True)

        # 📆 Filtros únicos
        meses = sorted(df['criado em'].dt.strftime('%B').unique())
        redes = sorted(df['nome da rede'].dropna().unique())
        situacoes = sorted(df['situacao do voucher'].dropna().unique())

        # 🎛️ Dropdowns
        filtros = dbc.Row([
            dbc.Col(dcc.Dropdown(options=[{'label': m, 'value': m} for m in meses],
                                 id='filtro-mes', placeholder="Mês", multi=True), md=4),
            dbc.Col(dcc.Dropdown(options=[{'label': r, 'value': r} for r in redes],
                                 id='filtro-rede', placeholder="Rede", multi=True), md=4),
            dbc.Col(dcc.Dropdown(options=[{'label': s, 'value': s} for s in situacoes],
                                 id='filtro-situacao', placeholder="Situação do voucher", multi=True), md=4)
        ])

        return filtros, gerar_kpis(df), gerar_graficos(df), gerar_ranking(df), ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar arquivo: {str(e)}"

# 🎯 Callbacks de atualização dinâmica
@app.callback(
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('ranking-vendedores', 'children'),
    Input('filtro-mes', 'value'),
    Input('filtro-rede', 'value'),
    Input('filtro-situacao', 'value'),
    State('upload-data', 'contents')
)
def aplicar_filtros(meses, redes, situacoes, contents):
    if contents is None:
        return dash.no_update, dash.no_update, dash.no_update

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))
    df.columns = [unidecode(c).strip().lower() for c in df.columns]
    df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
    df.dropna(subset=['criado em'], inplace=True)

    # Aplicar filtros
    if meses:
        df = df[df['criado em'].dt.strftime('%B').isin(meses)]
    if redes:
        df = df[df['nome da rede'].isin(redes)]
    if situacoes:
        df = df[df['situacao do voucher'].isin(situacoes)]

    return gerar_kpis(df), gerar_graficos(df), gerar_ranking(df)


# 🔢 KPIs
def gerar_kpis(df):
    total = df.shape[0]
    unicos = df['imei'].nunique()
    captacao = df['valor do voucher'].sum()
    ticket = captacao / unicos if unicos > 0 else 0
    utilizados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    conversao = len(utilizados) / total * 100 if total > 0 else 0

    return dbc.Row([
        dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(f"{total}")], body=True, color="dark", inverse=True), md=2),
        dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(f"{unicos}")], body=True, color="dark", inverse=True), md=2),
        dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")], body=True, color="dark", inverse=True), md=2),
        dbc.Col(dbc.Card([html.H5("🎫 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")], body=True, color="dark", inverse=True), md=2),
        dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")], body=True, color="dark", inverse=True), md=2),
    ])

# 📊 Gráficos
def gerar_graficos(df):
    utilizados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    df['data'] = df['criado em'].dt.date
    utilizados['data'] = utilizados['criado em'].dt.date

    fig1 = px.line(df.groupby('data').size().reset_index(name='Qtd'), x='data', y='Qtd', title="📅 Vouchers Gerados por Dia")
    fig2 = px.line(utilizados.groupby('data').size().reset_index(name='Qtd'), x='data', y='Qtd', title="📅 Vouchers Utilizados por Dia")
    fig3 = px.line(utilizados.groupby('data')['valor do voucher'].mean().reset_index(name='Média'), x='data', y='Média', title="🎟️ Ticket Médio Diário")

    return dbc.Row([
        dbc.Col(dcc.Graph(figure=fig1), md=4),
        dbc.Col(dcc.Graph(figure=fig2), md=4),
        dbc.Col(dcc.Graph(figure=fig3), md=4),
    ])

# 🏆 Ranking
def gerar_ranking(df):
    utilizados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    ranking = utilizados.groupby(['nome do vendedor', 'nome da filial', 'nome da rede']).size().reset_index(name='Qtd')
    top10 = ranking.sort_values(by='Qtd', ascending=False).head(10)

    return html.Div([
        html.H5("🏆 Top 10 Vendedores por Volume de Vouchers", style={'marginTop': 30}),
        dash_table.DataTable(
            columns=[{"name": col, "id": col} for col in top10.columns],
            data=top10.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            style_header={'backgroundColor': 'black', 'color': 'white'}
        )
    ])

# 🚀 Init
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
