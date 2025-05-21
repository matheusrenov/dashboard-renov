import dash
from dash import dcc, html, Input, Output, State, dash_table, ctx
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import io
import base64
import os

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard de Resultados"

# Layout
app.layout = dbc.Container(fluid=True, children=[
    html.H1("Dashboard de Resultados", className="text-center my-4"),

    dcc.Upload(
        id='upload-data',
        children=html.Div(["📁 Arraste ou selecione o arquivo .xlsx"]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center', 'marginBottom': '20px'
        },
        multiple=False
    ),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do voucher', multi=True), md=4),
    ], className='mb-4'),

    dcc.Store(id='hidden-data'),
    dcc.Store(id='filtered-data'),

    dbc.Row(id='kpi-container', className='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4),
    ])
])


# Upload callback
@app.callback(
    Output('hidden-data', 'data'),
    Input('upload-data', 'contents'),
    prevent_initial_call=True
)
def processar_arquivo(contents):
    if contents is None:
        return dash.no_update

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))
    df.columns = df.columns.str.strip()

    if 'Criado em' not in df.columns:
        return dash.no_update

    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df[df['Criado em'].notna()]
    df['Mês'] = df['Criado em'].dt.month_name(locale='pt_BR')

    return df.to_json(date_format='iso', orient='split')


# Atualizar filtros
@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('month-filter', 'value'),
    Output('filtered-data', 'data'),
    Input('hidden-data', 'data'),
)
def atualizar_filtros(json_data):
    if json_data is None:
        return [], [], [], None, dash.no_update

    df = pd.read_json(io.StringIO(json_data), orient='split')
    meses = sorted(df['Mês'].dropna().unique().tolist(), reverse=True)
    redes = sorted(df['Nome da rede'].dropna().unique())
    situacoes = sorted(df['Situacao do voucher'].dropna().unique())

    ultimo_mes = meses[0] if meses else None
    df_filtrado = df[df['Mês'] == ultimo_mes]

    return (
        [{'label': m, 'value': m} for m in meses],
        [{'label': r, 'value': r} for r in redes],
        [{'label': s, 'value': s} for s in situacoes],
        ultimo_mes,
        df_filtrado.to_json(date_format='iso', orient='split')
    )


# Aplicar filtros
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


# Dashboard KPIs + Gráficos
@app.callback(
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Input('filtered-data', 'data')
)
def update_dashboard(json_data):
    if json_data is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']

    total_gerados = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados['Valor do voucher'].sum()
    ticket_medio = df_utilizados['Valor do voucher'].mean() if total_utilizados else 0
    conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0

    kpis = [
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("📦 Dispositivos Captados", className="card-title text-white"),
                html.H3(f"{total_utilizados}", className="text-success"),
                html.P("Variação:", className="card-text text-muted")
            ])
        ], color="dark", inverse=True), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("💰 Captação Total", className="card-title text-white"),
                html.H3(f"R$ {valor_total:,.2f}", className="text-warning"),
                html.P("Variação:", className="card-text text-muted")
            ])
        ], color="dark", inverse=True), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("📊 Ticket Médio", className="card-title text-white"),
                html.H3(f"R$ {ticket_medio:,.2f}", className="text-info"),
                html.P("Variação:", className="card-text text-muted")
            ])
        ], color="dark", inverse=True), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("📈 Conversão", className="card-title text-white"),
                html.H3(f"{conversao:.2f}%", className="text-primary"),
                html.P("Variação:", className="card-text text-muted")
            ])
        ], color="dark", inverse=True), md=3),
    ]

    fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(df_utilizados, x='Criado em', title='Vouchers Utilizados por Dia')
    fig_ticket = px.line(
        df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(),
        x='Criado em', y='Valor do voucher', title='Ticket Médio Diário'
    )

    return kpis, fig_gerados, fig_utilizados, fig_ticket


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
