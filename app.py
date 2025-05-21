import os
import base64
import io
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.title = "Dashboard de Resultados"

app.layout = html.Div([
    html.H2("Dashboard de Resultados", className="text-center mt-3 mb-4"),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '2px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'marginBottom': '20px',
        },
        multiple=False
    ),

    html.Div(id='erro-upload', style={'color': 'red', 'textAlign': 'center'}),

    html.Div([
        dbc.Row([
            dbc.Col(dcc.Dropdown(id='month-filter', placeholder="Mês"), md=3),
            dbc.Col(dcc.Dropdown(id='rede-filter', placeholder="Nome da rede"), md=5),
            dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder="Situação do voucher"), md=4),
        ], className="mb-3"),

        html.Div(id='kpi-cards', className="mb-4"),

        dbc.Row([
            dbc.Col(dcc.Graph(id='grafico-gerados'), md=4),
            dbc.Col(dcc.Graph(id='grafico-utilizados'), md=4),
            dbc.Col(dcc.Graph(id='grafico-ticket'), md=4),
        ]),
        
        html.Hr(),

        html.H5("Ranking de Vendedores", className="mt-4 mb-2"),
        dash_table.DataTable(id='tabela-vendedores', style_table={'overflowX': 'auto'}, style_cell={'textAlign': 'left'}, page_size=20),

        html.Hr(),

        html.H5("Top Dispositivos", className="mt-4 mb-2"),
        dcc.Graph(id='grafico-top-dispositivos'),
    ]),

    dcc.Store(id='filtered-data')
])

@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('month-filter', 'value'),
    Output('filtered-data', 'data'),
    Output('erro-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
)
def atualizar_filtros(contents, filename):
    if contents is None:
        return [], [], [], None, None, ""

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        return [], [], [], None, None, f"Erro ao processar arquivo: {e}"

    df.columns = df.columns.str.strip().str.lower()

    col_map = {
        'mês': 'mes',
        'nome da rede': 'rede',
        'situação do voucher': 'situacao',
        'criado em': 'criado_em',
        'valor do voucher': 'valor',
        'nome do vendedor': 'vendedor',
        'nome da filial': 'filial'
    }

    df.rename(columns={c: col_map.get(c, c) for c in df.columns}, inplace=True)

    if 'criado_em' in df.columns:
        df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
    else:
        return [], [], [], None, None, "Erro: coluna 'Criado em' não encontrada."

    df['mes'] = df['criado_em'].dt.strftime('%b')

    month_options = [{'label': m, 'value': m} for m in sorted(df['mes'].dropna().unique())]
    rede_options = [{'label': r, 'value': r} for r in sorted(df['rede'].dropna().unique())]
    situacao_options = [{'label': s, 'value': s} for s in sorted(df['situacao'].dropna().unique())]

    latest_month = df['mes'].dropna().sort_values().unique()[-1] if len(df['mes'].dropna()) > 0 else None

    return month_options, rede_options, situacao_options, latest_month, df.to_json(date_format='iso', orient='split'), ""

@app.callback(
    Output('kpi-cards', 'children'),
    Output('grafico-gerados', 'figure'),
    Output('grafico-utilizados', 'figure'),
    Output('grafico-ticket', 'figure'),
    Output('tabela-vendedores', 'data'),
    Output('tabela-vendedores', 'columns'),
    Output('grafico-top-dispositivos', 'figure'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value'),
    Input('filtered-data', 'data'),
)
def atualizar_dashboard(mes, rede, situacao, data_json):
    if data_json is None:
        raise dash.exceptions.PreventUpdate

    df = pd.read_json(data_json, orient='split')

    # Garantir datetime
    if not pd.api.types.is_datetime64_any_dtype(df['criado_em']):
        df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')

    if mes:
        try:
            df = df[df['criado_em'].dt.strftime('%b') == mes]
        except Exception as e:
            print(f"[ERRO] Filtro por mês falhou: {e}")

    if rede:
        df = df[df['rede'] == rede]

    if situacao:
        df = df[df['situacao'] == situacao]

    # KPIs
    dispositivos = len(df)
    utilizados = df[df['situacao'] == 'UTILIZADO']
    captacao = utilizados['valor'].sum()
    ticket_medio = utilizados['valor'].mean()
    conversao = len(utilizados) / dispositivos * 100 if dispositivos > 0 else 0

    kpis = dbc.Row([
        dbc.Col(html.Div([
            html.H6("📦 Vouchers Gerados"),
            html.H4(f"{dispositivos}")
        ], className="p-3 bg-dark text-white border rounded"), md=3),
        dbc.Col(html.Div([
            html.H6("💰 Captação Total"),
            html.H4(f"R$ {captacao:,.2f}".replace('.', '_').replace(',', '.').replace('_', ','))
        ], className="p-3 bg-dark text-white border rounded"), md=3),
        dbc.Col(html.Div([
            html.H6("📊 Ticket Médio"),
            html.H4(f"R$ {ticket_medio:,.2f}".replace('.', '_').replace(',', '.').replace('_', ','))
        ], className="p-3 bg-dark text-white border rounded"), md=3),
        dbc.Col(html.Div([
            html.H6("📈 Conversão"),
            html.H4(f"{conversao:.2f}%")
        ], className="p-3 bg-dark text-white border rounded"), md=3),
    ])

    # Gráficos
    fig_gerados = px.line(df, x='criado_em', title="Vouchers Gerados por Dia")
    fig_utilizados = px.line(utilizados, x='criado_em', title="Vouchers Utilizados por Dia")
    fig_ticket = px.line(utilizados, x='criado_em', y='valor', title="Ticket Médio Diário")

    for fig in [fig_gerados, fig_utilizados, fig_ticket]:
        fig.update_layout(xaxis_title="Data", yaxis_title="", template="simple_white", xaxis_tickformat="%d %b")

    # Ranking
    ranking = utilizados.groupby(['vendedor', 'filial'])['valor'].count().reset_index(name='vouchers_utilizados')
    ranking.sort_values(by='vouchers_utilizados', ascending=False, inplace=True)
    ranking.insert(0, 'Ranking', range(1, len(ranking) + 1))

    ranking_data = ranking.to_dict('records')
    ranking_columns = [{"name": i, "id": i} for i in ranking.columns]

    # Top dispositivos
    if 'descricao' in df.columns:
        top_dispositivos = df['descricao'].value_counts().head(10).reset_index()
        top_dispositivos.columns = ['descricao', 'quantidade']
        fig_dispositivos = px.bar(top_dispositivos, x='descricao', y='quantidade', title="Top Dispositivos")
        fig_dispositivos.update_layout(xaxis_tickangle=-45)
    else:
        fig_dispositivos = {}

    return kpis, fig_gerados, fig_utilizados, fig_ticket, ranking_data, ranking_columns, fig_dispositivos

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
