import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import base64
import io
import os
import calendar
import json

# App Init
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

app.title = "Dashboard Trade-in - Renov"

# Colunas obrigatórias e aliases
REQUIRED_COLUMNS = [
    'Criado em', 'Situacao do voucher', 'Valor do voucher',
    'Nome da rede', 'Nome do vendedor', 'Nome da filial', 'Descrição',
    'Valor do dispositivo', 'Boost sell in', 'Boost sell out', 'Boost serviço sell out'
]

COLUMN_ALIASES = {
    'Criado em': ['Criado em', 'Data de criação'],
    'Situacao do voucher': ['Situacao do voucher', 'Situação do voucher'],
    'Valor do voucher': ['Valor do voucher'],
    'Nome da rede': ['Nome da rede', 'Rede'],
    'Nome do vendedor': ['Nome do vendedor', 'Vendedor'],
    'Nome da filial': ['Nome da filial', 'Filial'],
    'Descrição': ['Descrição', 'Produto'],
    'Valor do dispositivo': ['Valor do dispositivo'],
    'Boost sell in': ['Boost sell in'],
    'Boost sell out': ['Boost sell out'],
    'Boost serviço sell out': ['Boost serviço sell out']
}

def encontrar_coluna_padrao(colunas, nome_padrao):
    for alias in COLUMN_ALIASES[nome_padrao]:
        for col in colunas:
            if col.strip().lower() == alias.strip().lower():
                return col
    return None

def process_data(contents):
    print("[DEBUG] Iniciando leitura de conteúdo base64...")
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))
    df.columns = df.columns.str.strip()

    print("[DEBUG] Colunas da planilha:", df.columns.tolist())

    col_map = {}
    for padrao in REQUIRED_COLUMNS:
        encontrado = encontrar_coluna_padrao(df.columns, padrao)
        if encontrado:
            col_map[padrao] = encontrado
        else:
            raise ValueError(f"❌ Coluna obrigatória ausente: {padrao}")

    df.rename(columns={v: k for k, v in col_map.items()}, inplace=True)
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df[df['Criado em'].notna()]
    df['Mês'] = df['Criado em'].dt.month

    print(f"[DEBUG] Planilha processada com sucesso. Total de linhas: {len(df)}")
    return df
app.layout = dbc.Container(fluid=True, children=[
    html.H2("📊 Dashboard de Resultados - Renov", className="text-center my-4"),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📤 Clique ou arraste o arquivo Excel com os dados']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
            'textAlign': 'center', 'backgroundColor': '#f9f9f9',
            'marginBottom': '20px'
        },
        multiple=False
    ),

    html.Div(id='upload-debug-msg', style={'color': 'red'}),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação', multi=True), md=4),
    ], className="mb-4"),

    dcc.Tabs(id='tabs', value='visao-geral', children=[
        dcc.Tab(label='📈 Visão Geral', value='visao-geral'),
        dcc.Tab(label='🏆 Performance', value='performance')
    ]),
    html.Div(id='tabs-content'),

    dcc.Store(id='hidden-data'),
    dcc.Store(id='filtered-data')
])
@app.callback(
    [Output('hidden-data', 'data'),
     Output('upload-debug-msg', 'children')],
    Input('upload-data', 'contents')
)
def carregar_dados(contents):
    if contents is None:
        return dash.no_update, ""
    try:
        df = process_data(contents)
        return df.to_json(date_format='iso', orient='split'), "✅ Arquivo processado com sucesso!"
    except Exception as e:
        print("[ERRO no process_data()]", str(e))
        return dash.no_update, f"❌ Erro: {str(e)}"

@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Input('hidden-data', 'data')
)
def preencher_filtros(json_data):
    if json_data is None:
        return [], [], []

    df = pd.read_json(io.StringIO(json_data), orient='split')
    meses = sorted(df['Mês'].dropna().unique())
    nomes_meses = {i: calendar.month_name[i].capitalize() for i in meses}

    return (
        [{'label': nomes_meses[m], 'value': m} for m in meses],
        [{'label': r, 'value': r} for r in sorted(df['Nome da rede'].dropna().unique())],
        [{'label': s, 'value': s} for s in sorted(df['Situacao do voucher'].dropna().unique())]
    )

@app.callback(
    Output('filtered-data', 'data'),
    Input('hidden-data', 'data'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value')
)
def aplicar_filtros(json_data, mes, rede, situacoes):
    if json_data is None:
        return dash.no_update
    df = pd.read_json(io.StringIO(json_data), orient='split')

    if mes:
        df = df[df['Mês'] == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacoes:
        df = df[df['Situacao do voucher'].isin(situacoes)]

    return df.to_json(date_format='iso', orient='split')
@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value'),
    Input('filtered-data', 'data')
)
def renderizar_abas(tab, json_data):
    if json_data is None:
        return html.Div("⚠️ Faça upload de uma planilha válida para visualizar os dados.")

    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']

    total_gerados = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados['Valor do voucher'].sum()
    valor_total_dispositivo = df_utilizados['Valor do dispositivo'].sum()
    boosts = df_utilizados[['Boost sell in', 'Boost sell out', 'Boost serviço sell out']].fillna(0).sum(axis=1)
    boost_total = boosts.sum()
    ticket_medio = valor_total / total_utilizados if total_utilizados else 0
    custo_medio = valor_total_dispositivo / total_utilizados if total_utilizados else 0
    conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0
    percentual_boost = (boosts.gt(0).sum() / total_utilizados * 100) if total_utilizados else 0

    if tab == 'visao-geral':
        kpis = dbc.Row([
            dbc.Col(html.Div([
                html.H5("📦 Dispositivos Captados"),
                html.H4(total_utilizados)
            ], className="border p-3 bg-light"), md=3),
            dbc.Col(html.Div([
                html.H5("💰 Captação Total"),
                html.H4(f"R$ {valor_total:,.2f}")
            ], className="border p-3 bg-light"), md=3),
            dbc.Col(html.Div([
                html.H5("📊 Ticket Médio"),
                html.H4(f"R$ {ticket_medio:,.2f}")
            ], className="border p-3 bg-light"), md=3),
            dbc.Col(html.Div([
                html.H5("📈 Conversão"),
                html.H4(f"{conversao:.2f}%")
            ], className="border p-3 bg-light"), md=3),
        ], className="mb-4")

        fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
        fig_utilizados = px.histogram(df_utilizados, x='Criado em', title='Vouchers Utilizados por Dia')
        fig_ticket = px.line(df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(), x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

        return html.Div([
            kpis,
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
                dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
                dbc.Col(dcc.Graph(figure=fig_ticket), md=4)
            ])
        ])

    elif tab == 'performance':
        ranking_df = df_utilizados.groupby(['Nome do vendedor', 'Nome da filial', 'Nome da rede']) \
            .size().reset_index(name='Quantidade')
        ranking_df['Ranking'] = ranking_df['Quantidade'].rank(method='first', ascending=False).astype(int)
        ranking_df = ranking_df.sort_values(by='Ranking')
        top_vendedores_data = ranking_df.to_dict('records')
        top_vendedores_columns = [{'name': col, 'id': col} for col in ranking_df.columns]

        top_dispositivos_df = df['Descrição'].value_counts().nlargest(10).reset_index()
        top_dispositivos_df.columns = ['Descrição', 'Quantidade']
        fig_dispositivos = px.bar(top_dispositivos_df, x='Descrição', y='Quantidade', text='Quantidade', title='Top 10 Dispositivos')
        fig_dispositivos.update_traces(textposition='outside')

        campanha_cols = ['Boost sell in', 'Boost sell out', 'Boost serviço sell out']
        campanha_sum = df_utilizados[campanha_cols].fillna(0).sum().reset_index()
        campanha_sum.columns = ['Campanha', 'Valor']
        fig_campanhas = px.bar(campanha_sum, x='Campanha', y='Valor', title='Captação por Campanha (Boosts)')

        return html.Div([
            dbc.Row([
                dbc.Col(dash_table.DataTable(data=top_vendedores_data, columns=top_vendedores_columns,
                                             style_table={'overflowX': 'auto'}), md=6),
                dbc.Col(dcc.Graph(figure=fig_dispositivos), md=6)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_campanhas), md=12)
            ])
        ])
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
