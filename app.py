import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import io
import base64
import calendar
import os
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard de Resultados"

REQUIRED_COLUMNS = [
    'Criado em', 'Situacao do voucher', 'Valor do voucher',
    'Nome da rede', 'Nome do vendedor', 'Nome da filial', 'Descrição'
]

COLUMN_ALIASES = {
    'Criado em': ['Criado em', 'Data de criação', 'Data criação'],
    'Situacao do voucher': ['Situacao do voucher', 'Situação do voucher'],
    'Valor do voucher': ['Valor do voucher', 'Valor Voucher', 'Valor'],
    'Nome da rede': ['Nome da rede', 'Rede'],
    'Nome do vendedor': ['Nome do vendedor', 'Vendedor'],
    'Nome da filial': ['Nome da filial', 'Filial'],
    'Descrição': ['Descrição', 'Descricao', 'Produto']
}

# Util functions
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
    df['Mês'] = df['Criado em'].dt.month
    df['Nome do mês'] = df['Criado em'].dt.strftime('%B')
    return df

# KPI card component
def kpi_card(title, value, icon=""):
    return dbc.Card(
        dbc.CardBody([
            html.H6(f"{icon} {title}", className="card-title"),
            html.H3(value, className="card-text")
        ]),
        className="shadow-sm",
        style={"backgroundColor": "#1e1e1e", "color": "white", "border": "2px solid #00C896"}
    )

app.layout = dbc.Container(fluid=True, children=[
    html.H1("Dashboard de Resultados", style={"textAlign": "center", "marginTop": "20px"}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(["📁 Arraste ou selecione o arquivo .xlsx"]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
            'textAlign': 'center', 'marginBottom': '20px'
        },
        multiple=False
    ),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do voucher', multi=True), md=4)
    ], className="mb-4"),

    dbc.Row(id='kpi-container', className='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4)
    ]),

    dbc.Row([
        dbc.Col([
            dash_table.DataTable(
                id='top-vendedores',
                columns=[], data=[],
                style_table={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'maxHeight': '400px',
                    'width': '100%',
                },
                style_cell={
                    'fontSize': '12px',
                    'padding': '5px',
                    'textAlign': 'left',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                    'maxWidth': '200px',
                    'minWidth': '80px',
                },
                style_header={
                    'fontWeight': 'bold',
                    'backgroundColor': '#f9f9f9'
                },
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Ranking'},
                        'textAlign': 'center',
                        'width': '60px'
                    }
                ],
                page_action='none',
                fixed_rows={'headers': True},
                style_as_list_view=True,
            )
        ], md=6),

        dbc.Col(dcc.Graph(id='top-dispositivos'), md=6)
    ], className="mt-4"),

    dcc.Store(id='filtered-data')
])

@app.callback(
    Output('month-filter', 'options'),
    Output('month-filter', 'value'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('filtered-data', 'data'),
    Input('upload-data', 'contents')
)
def carregar_dados(contents):
    if contents is None:
        return [], None, [], [], None

    try:
        df = process_data(contents)
        meses = sorted(df['Nome do mês'].dropna().unique(), key=lambda x: datetime.strptime(x, "%B"))
        redes = sorted(df['Nome da rede'].dropna().unique())
        situacoes = sorted(df['Situacao do voucher'].dropna().unique())

        options_mes = [{'label': m, 'value': m} for m in meses]
        options_rede = [{'label': r, 'value': r} for r in redes]
        options_sit = [{'label': s, 'value': s} for s in situacoes]

        mes_mais_recente = df['Criado em'].max().strftime('%B')
        return options_mes, mes_mais_recente, options_rede, options_sit, df.to_json(date_format='iso', orient='split')
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return [], None, [], [], None

@app.callback(
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Output('top-vendedores', 'data'),
    Output('top-vendedores', 'columns'),
    Output('top-dispositivos', 'figure'),
    Input('filtered-data', 'data'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value')
)
def atualizar_dashboard(json_data, mes, rede, situacao):
    if json_data is None:
        return [], dash.no_update, dash.no_update, dash.no_update, [], [], dash.no_update

    df = pd.read_json(io.StringIO(json_data), orient='split')

    if mes:
        df = df[df['Nome do mês'] == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacao:
        df = df[df['Situacao do voucher'].isin(situacao)]

    df_utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']

    total_vouchers = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados['Valor do voucher'].sum()
    ticket_medio = df_utilizados['Valor do voucher'].mean() if total_utilizados else 0
    conversao = (total_utilizados / total_vouchers) * 100 if total_vouchers else 0

    kpis = [
        dbc.Col(kpi_card("Vouchers Gerados", str(total_vouchers), icon="📊"), md=3),
        dbc.Col(kpi_card("Dispositivos Captados", str(total_utilizados), icon="📦"), md=3),
        dbc.Col(kpi_card("Captação Total", f"R$ {valor_total:,.2f}", icon="💰"), md=3),
        dbc.Col(kpi_card("Ticket Médio", f"R$ {ticket_medio:,.2f}", icon="📈"), md=3)
    ]

    fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(df_utilizados, x='Criado em', title='Vouchers Utilizados por Dia')

    fig_ticket = px.line(
        df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(),
        x='Criado em',
        y='Valor do voucher',
        title='Ticket Médio Diário'
    )

    ranking_df = df_utilizados.groupby(
        ['Nome do vendedor', 'Nome da filial']
    ).size().reset_index(name='Quantidade')

    ranking_df['Ranking'] = ranking_df['Quantidade'].rank(method='first', ascending=False).astype(int)
    ranking_df = ranking_df.sort_values(by='Ranking')
    ranking_df = ranking_df[['Ranking', 'Nome do vendedor', 'Nome da filial', 'Quantidade']]

    top_vendedores_data = ranking_df.to_dict('records')
    top_vendedores_columns = [{'name': col, 'id': col} for col in ranking_df.columns]

    top_dispositivos_df = df['Descrição'].value_counts().nlargest(10).reset_index()
    top_dispositivos_df.columns = ['Descrição', 'Quantidade']

    fig_dispositivos = px.bar(top_dispositivos_df, x='Descrição', y='Quantidade', title='Top Dispositivos')
    fig_dispositivos.update_layout(xaxis_tickangle=-45)

    return kpis, fig_gerados, fig_utilizados, fig_ticket, top_vendedores_data, top_vendedores_columns, fig_dispositivos

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
