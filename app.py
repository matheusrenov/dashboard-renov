import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import pandas as pd
import plotly.express as px
import base64
import io
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

app.title = 'Dashboard de Resultados'

# ========= Layout ========= #
app.layout = dbc.Container([
    html.H2("Dashboard de Resultados", className="text-center my-4"),

    dcc.Upload(
        id='upload-data',
        children=html.Div([
            "📁 Arraste ou selecione o arquivo .xlsx"
        ]),
        style={
            'width': '100%',
            'height': '80px',
            'lineHeight': '80px',
            'borderWidth': '2px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'marginBottom': '10px'
        },
        multiple=False
    ),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder="Mês"), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder="Nome da rede"), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder="Situação do voucher"), md=4),
    ], className="mb-4"),

    dcc.Store(id='filtered-data'),

    dbc.Row([
        dbc.Col(html.Div(id='kpi-vouchers-gerados'), md=3),
        dbc.Col(html.Div(id='kpi-dispositivos'), md=3),
        dbc.Col(html.Div(id='kpi-captacao'), md=3),
        dbc.Col(html.Div(id='kpi-ticket-medio'), md=3),
        dbc.Col(html.Div(id='kpi-conversao'), md=3),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico-gerados'), md=4),
        dbc.Col(dcc.Graph(id='grafico-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='grafico-ticket'), md=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dash_table.DataTable(id='tabela-vendedores',
                                     style_table={'overflowX': 'auto'},
                                     style_cell={'textAlign': 'left', 'minWidth': '100px', 'fontSize': 12}),
                md=6),
        dbc.Col(dcc.Graph(id='grafico-top-dispositivos'), md=6)
    ])
], fluid=True)


# ========= Callbacks ========= #
@app.callback(
    Output('filtered-data', 'data'),
    Output('month-filter', 'options'),
    Output('month-filter', 'value'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def load_and_prepare(content, filename):
    if content is None:
        return dash.no_update, [], None, [], []

    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)

    try:
        df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        return dash.no_update, [], None, [], []

    # Tratamento da data
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')

    # Normalização de coluna com possíveis variações no nome
    col_map = {col: col.strip().lower() for col in df.columns}
    situacao_col = next((col for col in df.columns if 'situacao do voucher' in col.lower()), None)
    if situacao_col is None:
        return dash.no_update, [], None, [], []

    # Opções de filtro
    df['Mês'] = df['Criado em'].dt.strftime('%b')
    meses = sorted(df['Mês'].dropna().unique(), key=lambda x: datetime.strptime(x, "%b"))
    redes = sorted(df['Nome da rede'].dropna().unique())
    situacoes = sorted(df[situacao_col].dropna().unique())

    return df.to_json(date_format='iso', orient='split'), [{'label': m, 'value': m} for m in meses], meses[-1], [{'label': r, 'value': r} for r in redes], [{'label': s, 'value': s} for s in situacoes]


@app.callback(
    Output('kpi-vouchers-gerados', 'children'),
    Output('kpi-dispositivos', 'children'),
    Output('kpi-captacao', 'children'),
    Output('kpi-ticket-medio', 'children'),
    Output('kpi-conversao', 'children'),
    Output('grafico-gerados', 'figure'),
    Output('grafico-utilizados', 'figure'),
    Output('grafico-ticket', 'figure'),
    Output('tabela-vendedores', 'data'),
    Output('tabela-vendedores', 'columns'),
    Output('grafico-top-dispositivos', 'figure'),
    Input('filtered-data', 'data'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value')
)
def atualizar_dashboard(json_data, mes, rede, situacao):
    if json_data is None:
        raise dash.exceptions.PreventUpdate

    df = pd.read_json(json_data, orient='split')
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df['Mês'] = df['Criado em'].dt.strftime('%b')

    situacao_col = next((col for col in df.columns if 'situacao do voucher' in col.lower()), None)

    if mes:
        df = df[df['Mês'] == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacao:
        df = df[df[situacao_col] == situacao]

    # KPIs
    total_vouchers = len(df)
    dispositivos = df['Número de série'].nunique()
    captacao = df[df[situacao_col] == 'UTILIZADO']['Valor do voucher'].sum()
    ticket = df[df[situacao_col] == 'UTILIZADO']['Valor do voucher'].mean()
    conversao = (df[df[situacao_col] == 'UTILIZADO'].shape[0] / df.shape[0]) * 100 if df.shape[0] > 0 else 0

    def card_kpi(title, value):
        return dbc.Card([
            dbc.CardBody([
                html.H6(title, className="card-title"),
                html.H4(value, className="card-text")
            ])
        ], style={'background': '#1e1e1e', 'color': 'white', 'border': '1px solid #1abc9c'})

    # Gráficos
    fig_gerados = px.line(df, x='Criado em', title='Vouchers Gerados por Dia') if not df.empty else px.line()
    fig_utilizados = px.line(df[df[situacao_col] == 'UTILIZADO'], x='Criado em', title='Vouchers Utilizados por Dia') if not df.empty else px.line()
    fig_ticket = px.line(df[df[situacao_col] == 'UTILIZADO'], x='Criado em', y='Valor do voucher', title='Ticket Médio Diário') if not df.empty else px.line()

    # Ranking vendedores
    ranking = df[df[situacao_col] == 'UTILIZADO'].groupby(['Nome do vendedor', 'Nome da filial'])['Número do voucher'].count().reset_index()
    ranking = ranking.rename(columns={'Número do voucher': 'Qtd'})
    ranking = ranking.sort_values(by='Qtd', ascending=False).head(20).reset_index(drop=True)
    ranking.insert(0, 'Ranking', range(1, len(ranking) + 1))

    data = ranking.to_dict('records')
    columns = [{"name": col, "id": col} for col in ranking.columns]

    # Top dispositivos
    top_dispositivos = df[df[situacao_col] == 'UTILIZADO']['Descrição'].value_counts().reset_index()
    top_dispositivos.columns = ['Descrição', 'Quantidade']
    fig_top_dispositivos = px.bar(top_dispositivos.head(10), x='Descrição', y='Quantidade', title='Top Dispositivos')

    return (
        card_kpi("📊 Vouchers Gerados", f"{total_vouchers}"),
        card_kpi("📦 Dispositivos Captados", f"{dispositivos}"),
        card_kpi("💰 Captação Total", f"R$ {captacao:,.2f}"),
        card_kpi("📉 Ticket Médio", f"R$ {ticket:,.2f}"),
        card_kpi("📈 Conversão", f"{conversao:.2f}%"),
        fig_gerados,
        fig_utilizados,
        fig_ticket,
        data,
        columns,
        fig_top_dispositivos
    )


# ========= Run ========= #
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
