import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import base64
import io
import os

# Inicialização do app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard de Resultados"

# Variáveis globais
REQUIRED_COLUMNS = ['Criado em', 'Situacao do voucher', 'Valor do voucher', 'Nome da rede',
                    'Nome do vendedor', 'Nome da filial', 'Descrição']

COLUMN_ALIASES = {
    'Criado em': ['Criado em', 'Data de criação'],
    'Situacao do voucher': ['Situacao do voucher', 'Situação do voucher'],
    'Valor do voucher': ['Valor do voucher'],
    'Nome da rede': ['Nome da rede'],
    'Nome do vendedor': ['Nome do vendedor'],
    'Nome da filial': ['Nome da filial'],
    'Descrição': ['Descrição']
}

def encontrar_coluna_padrao(colunas, nome_padrao):
    for alias in COLUMN_ALIASES[nome_padrao]:
        for col in colunas:
            if col.strip().lower() == alias.strip().lower():
                return col
    return None

def process_data(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))
    df.columns = df.columns.str.strip()

    col_map = {}
    for padrao in REQUIRED_COLUMNS:
        encontrado = encontrar_coluna_padrao(df.columns, padrao)
        if encontrado:
            col_map[padrao] = encontrado
        else:
            raise ValueError(f"Coluna obrigatória ausente: {padrao}")

    df.rename(columns={v: k for k, v in col_map.items()}, inplace=True)
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df[df['Criado em'].notna()]
    df['Mês'] = df['Criado em'].dt.strftime('%B')  # Nome do mês
    return df

# Layout
app.layout = dbc.Container(fluid=True, children=[
    html.Div([
        html.H1("Dashboard de Resultados", style={"textAlign": "center", "marginTop": "20px"}),
    ]),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
            'textAlign': 'center', 'margin': '20px 0', 'backgroundColor': '#f9f9f9'
        },
        multiple=False
    ),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do voucher', multi=True), md=4)
    ], className="mb-4"),

    dbc.Row(id='kpi-container', className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dash_table.DataTable(id='top-vendedores'), md=6),
        dbc.Col(dcc.Graph(id='top-dispositivos'), md=6),
    ]),

    dcc.Store(id='raw-data'),
    dcc.Store(id='filtered-data')
])

# CALLBACK: Processamento de upload
@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('month-filter', 'value'),
    Output('filtered-data', 'data'),
    Output('raw-data', 'data'),
    Input('upload-data', 'contents')
)
def atualizar_filtros(contents):
    if contents is None:
        return [], [], [], None, None, None

    try:
        df = process_data(contents)
    except Exception as e:
        return [], [], [], None, None, None

    meses = sorted(df['Mês'].dropna().unique(), key=lambda x: pd.to_datetime(x, format='%B', errors='coerce').month)
    redes = sorted(df['Nome da rede'].dropna().unique())
    situacoes = sorted(df['Situacao do voucher'].dropna().unique())
    mes_recente = meses[-1] if meses else None

    filtered = df[df['Mês'] == mes_recente]

    return (
        [{'label': m, 'value': m} for m in meses],
        [{'label': r, 'value': r} for r in redes],
        [{'label': s, 'value': s} for s in situacoes],
        mes_recente,
        filtered.to_json(date_format='iso', orient='split'),
        df.to_json(date_format='iso', orient='split')
    )

# CALLBACK: Atualização dos gráficos
@app.callback(
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Output('top-vendedores', 'data'),
    Output('top-vendedores', 'columns'),
    Output('top-dispositivos', 'figure'),
    Input('filtered-data', 'data')
)
def update_dashboard(json_data):
    if json_data is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, [], [], dash.no_update

    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']

    total_gerados = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados['Valor do voucher'].sum()
    ticket_medio = df_utilizados['Valor do voucher'].mean() if total_utilizados else 0
    conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0

    kpis = [
        dbc.Col(html.Div([
            html.H5("📦 Dispositivos Captados"),
            html.H4(f"{total_utilizados}")
        ], className="p-3 border rounded"), md=3),
        dbc.Col(html.Div([
            html.H5("💰 Captação Total"),
            html.H4(f"R$ {valor_total:,.2f}")
        ], className="p-3 border rounded"), md=3),
        dbc.Col(html.Div([
            html.H5("📊 Ticket Médio"),
            html.H4(f"R$ {ticket_medio:,.2f}")
        ], className="p-3 border rounded"), md=3),
        dbc.Col(html.Div([
            html.H5("📈 Conversão"),
            html.H4(f"{conversao:.2f}%")
        ], className="p-3 border rounded"), md=3),
    ]

    fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(df_utilizados, x='Criado em', title='Vouchers Utilizados por Dia')

    fig_ticket = px.line(
        df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(),
        x='Criado em',
        y='Valor do voucher',
        title='Ticket Médio Diário'
    )

    # Ranking de vendedores
    ranking_df = df_utilizados.groupby(['Nome do vendedor', 'Nome da filial', 'Nome da rede']) \
                              .size().reset_index(name='Quantidade')
    ranking_df['Ranking'] = ranking_df['Quantidade'].rank(method='first', ascending=False).astype(int)
    ranking_df = ranking_df.sort_values(by='Ranking')
    ranking_df = ranking_df[['Ranking', 'Nome do vendedor', 'Nome da filial', 'Nome da rede', 'Quantidade']]

    top_vendedores_data = ranking_df.to_dict('records')
    top_vendedores_columns = [{'name': col, 'id': col} for col in ranking_df.columns]

    top_dispositivos_df = df_utilizados['Descrição'].value_counts().nlargest(10).reset_index()
    top_dispositivos_df.columns = ['Descrição', 'Quantidade']

    fig_dispositivos = px.bar(top_dispositivos_df, x='Descrição', y='Quantidade', title='Top 10 Dispositivos')

    return kpis, fig_gerados, fig_utilizados, fig_ticket, top_vendedores_data, top_vendedores_columns, fig_dispositivos

# Execução
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
