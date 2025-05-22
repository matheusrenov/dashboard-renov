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

# 🔧 Inicialização
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# 📦 Layout
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

    html.Div(id='filtros'),
    html.Div(id='kpi-cards'),
    html.Div(id='graficos'),
    html.Div(id='ranking-vendedores')
])

# Filtros dinâmicos
@app.callback(
    Output('filtros', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def carregar_filtros(contents, filename):
    if contents is None:
        return ""
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))
    df.columns = [unidecode(col).strip().lower() for col in df.columns]

    df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
    df['mes'] = df['criado em'].dt.strftime('%b')

    return dbc.Row([
        dbc.Col(dcc.Dropdown(id='filtro-mes',
                             options=[{'label': m, 'value': m} for m in sorted(df['mes'].dropna().unique())],
                             placeholder='Mês', multi=True), md=4),
        dbc.Col(dcc.Dropdown(id='filtro-rede',
                             options=[{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())],
                             placeholder='Rede', multi=True), md=4),
        dbc.Col(dcc.Dropdown(id='filtro-situacao',
                             options=[{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())],
                             placeholder='Situação do voucher', multi=True), md=4)
    ], style={'marginTop': 20})

# Função de filtro central
def aplicar_filtros(df, mes, rede, situacao):
    df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
    df['mes'] = df['criado em'].dt.strftime('%b')

    if mes is not None and len(mes) > 0:
        df = df[df['mes'].isin(mes)]
    if rede is not None and len(rede) > 0:
        df = df[df['nome da rede'].isin(rede)]
    if situacao is not None and len(situacao) > 0:
        df = df[df['situacao do voucher'].isin(situacao)]

    return df

# Callback principal
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
def atualizar_dashboard(contents, filename, filtro_mes, filtro_rede, filtro_situacao):
    if contents is None:
        return dash.no_update, dash.no_update, dash.no_update, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        df.columns = [unidecode(col).strip().lower() for col in df.columns]

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes'] = df['criado em'].dt.strftime('%b')

        # 🔒 Blindagem
        colunas_obrigatorias = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher']
        for col in colunas_obrigatorias:
            if col not in df.columns:
                return dash.no_update, dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        # 🎯 Aplicar filtros
        df = aplicar_filtros(df, filtro_mes, filtro_rede, filtro_situacao)

        total_gerados = df.shape[0]
        dispositivos = df['imei'].nunique()
        captacao = df['valor do voucher'].sum()
        ticket = captacao / dispositivos if dispositivos > 0 else 0

        usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
        conversao = len(usados) / total_gerados * 100 if total_gerados > 0 else 0

        kpis = dbc.Row([
            dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(f"{total_gerados}")],
                             body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(f"{dispositivos}")],
                             body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")],
                             body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("🎯 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")],
                             body=True, color="dark", inverse=True), md=2),
            dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")],
                             body=True, color="dark", inverse=True), md=2),
        ])

        # 📈 Gráficos
        fig_gerados = px.line(df.groupby(df['criado em'].dt.date).size().reset_index(name='Qtd'),
                              x='criado em', y='Qtd', title="📆 Vouchers Gerados por Dia")
        fig_utilizados = px.line(usados.groupby(usados['criado em'].dt.date).size().reset_index(name='Qtd'),
                                 x='criado em', y='Qtd', title="📆 Vouchers Utilizados por Dia")
        fig_ticket = px.line(usados.groupby(usados['criado em'].dt.date)['valor do voucher'].mean().reset_index(name='Média'),
                             x='criado em', y='Média', title="🎫 Ticket Médio Diário")

        graficos = dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
            dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
            dbc.Col(dcc.Graph(figure=fig_ticket), md=4)
        ])

        # 🧑‍💼 Ranking de Vendedores (apenas utilizados)
        usados_rank = usados.groupby(['nome do vendedor', 'nome da filial', 'nome da rede']) \
                            .size().reset_index(name='Qtd') \
                            .sort_values(by='Qtd', ascending=False).head(10)

        ranking = html.Div([
            html.H5("🏆 Top 10 Vendedores por Volume de Vouchers"),
            dash_table.DataTable(
                columns=[{"name": col, "id": col} for col in usados_rank.columns],
                data=usados_rank.to_dict('records'),
                style_cell={'textAlign': 'left', 'whiteSpace': 'normal'},
                style_header={'fontWeight': 'bold', 'backgroundColor': 'black', 'color': 'white'},
            )
        ])

        return kpis, graficos, ranking, ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar arquivo: {str(e)}"

# 🚀 Execução
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
