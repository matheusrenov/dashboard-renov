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
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard de Resultados"

REQUIRED_COLUMNS = ['Criado em', 'Situacao do voucher', 'Valor do voucher', 'Nome da rede', 'Nome do vendedor', 'Nome da filial', 'Descrição']

# Layout principal
app.layout = dbc.Container(fluid=True, children=[
    html.H1("Dashboard de Resultados", style={"textAlign": "center", "marginTop": "10px"}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed',
            'borderRadius': '10px', 'textAlign': 'center',
            'marginBottom': '20px'
        },
        multiple=False
    ),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do voucher', multi=True), md=4),
    ], className='mb-4'),

    dbc.Row(id='kpi-container', className='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4)
    ], className='mb-4'),

    dbc.Row([
        dbc.Col(dash_table.DataTable(id='top-vendedores'), md=6),
        dbc.Col(dcc.Graph(id='top-dispositivos'), md=6)
    ], className='mb-4'),

    dcc.Store(id='raw-data'),
    dcc.Store(id='filtered-data')
])

# Callback para processar upload e gerar opções de filtro
@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('month-filter', 'value'),
    Output('filtered-data', 'data'),
    Output('raw-data', 'data'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def processar_upload(contents, filename):
    if contents is None:
        raise dash.exceptions.PreventUpdate

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))

    # Normaliza colunas
    df.columns = df.columns.str.strip()
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df[df['Criado em'].notna()]
    df['Mês'] = df['Criado em'].dt.month
    df['Nome do vendedor'] = df['Nome do vendedor'].astype(str)
    df['Nome da rede'] = df['Nome da rede'].astype(str)
    df['Situacao do voucher'] = df['Situacao do voucher'].astype(str)

    month_opts = [{'label': calendar.month_name[m], 'value': m} for m in sorted(df['Mês'].dropna().unique())]
    rede_opts = [{'label': rede, 'value': rede} for rede in sorted(df['Nome da rede'].dropna().unique())]
    status_opts = [{'label': s, 'value': s} for s in sorted(df['Situacao do voucher'].dropna().unique())]

    ultimo_mes = df['Mês'].max()

    return month_opts, rede_opts, status_opts, ultimo_mes, df.to_json(date_format='iso', orient='split'), df.to_json(date_format='iso', orient='split')


# Callback para aplicar filtros
@app.callback(
    Output('filtered-data', 'data'),
    Input('raw-data', 'data'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value'),
    prevent_initial_call=True
)
def aplicar_filtros(json_data, mes, rede, situacoes):
    if json_data is None:
        raise dash.exceptions.PreventUpdate

    df = pd.read_json(io.StringIO(json_data), orient='split')

    if mes:
        df = df[df['Mês'] == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacoes:
        df = df[df['Situacao do voucher'].isin(situacoes)]

    return df.to_json(date_format='iso', orient='split')


# Callback para gráficos e KPIs
@app.callback(
    Output('kpi-container', 'children'),
    Output('vouchers-gerados', 'figure'),
    Output('vouchers-utilizados', 'figure'),
    Output('ticket-medio', 'figure'),
    Output('top-vendedores', 'data'),
    Output('top-vendedores', 'columns'),
    Output('top-dispositivos', 'figure'),
    Input('filtered-data', 'data'),
    prevent_initial_call=True
)
def update_dashboard(json_data):
    if json_data is None:
        raise dash.exceptions.PreventUpdate

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
                html.H5("📦 Dispositivos Captados", className="card-title"),
                html.H2(f"{total_utilizados}")
            ])
        ]), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("💰 Captação Total", className="card-title"),
                html.H2(f"R$ {valor_total:,.2f}")
            ])
        ]), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("📊 Ticket Médio", className="card-title"),
                html.H2(f"R$ {ticket_medio:,.2f}")
            ])
        ]), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("📈 Conversão", className="card-title"),
                html.H2(f"{conversao:.2f}%")
            ])
        ]), md=3)
    ]

    fig_gerados = px.histogram(df, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(df_utilizados, x='Criado em', title='Vouchers Utilizados por Dia')
    fig_ticket = px.line(df_utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(),
                         x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

    # Ranking vendedores
    ranking = df_utilizados.groupby(['Nome do vendedor']).size().reset_index(name='Quantidade')
    ranking = ranking.sort_values(by='Quantidade', ascending=False).reset_index(drop=True)
    ranking['Ranking'] = ranking.index + 1
    ranking_data = ranking.to_dict('records')
    ranking_columns = [{"name": i, "id": i} for i in ranking.columns]

    # Top dispositivos
    top_dispositivos_df = df['Descrição'].value_counts().nlargest(10).reset_index()
    top_dispositivos_df.columns = ['Descrição', 'Quantidade']
    fig_dispositivos = px.bar(top_dispositivos_df, x='Descrição', y='Quantidade', title='Top Dispositivos')

    return kpis, fig_gerados, fig_utilizados, fig_ticket, ranking_data, ranking_columns, fig_dispositivos


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

