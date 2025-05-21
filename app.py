import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import base64
import io
import os
from datetime import datetime
import locale

# Tentativa de setar locale pt_BR
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass  # fallback para nome manual se der erro no servidor

# App init
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Logo base64
with open("renov-logo.png", "rb") as f:
    logo_encoded = base64.b64encode(f.read()).decode()

app.title = "Dashboard de Resultados"

app.layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        dbc.Col(html.H2("Dashboard de Resultados", style={'textAlign': 'center'}), md=10),
        dbc.Col(html.Img(src=f'data:image/png;base64,{logo_encoded}', height="50px"), md=2, style={'textAlign': 'right'})
    ], align="center", className="my-2"),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📤 Arraste ou selecione o arquivo .xlsx']),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '2px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
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
    ]),

    dbc.Row([
        dbc.Col(dash_table.DataTable(id='top-vendedores', style_table={'overflowX': 'auto'}), md=6),
        dbc.Col(dcc.Graph(id='top-dispositivos'), md=6)
    ], className='mt-4'),

    dcc.Store(id='filtered-data'),
    dcc.Store(id='hidden-data')
])

# CALLBACK PARA PROCESSAMENTO DE ARQUIVO
@app.callback(
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('month-filter', 'value'),
    Output('filtered-data', 'data'),
    Input('upload-data', 'contents'),
)
def process_file(contents):
    if not contents:
        return [], [], [], None, None

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_excel(io.BytesIO(decoded))
        df.columns = df.columns.str.strip()

        df = df.rename(columns=lambda col: col.strip())

        df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
        df = df.dropna(subset=['Criado em'])

        df['Mês'] = df['Criado em'].dt.strftime('%B').str.capitalize()
        meses = sorted(df['Mês'].dropna().unique(), key=lambda m: datetime.strptime(m, '%B').month)
        ultimo_mes = df['Mês'].value_counts().idxmax()

        redes = sorted(df['Nome da rede'].dropna().unique())
        situacoes = sorted(df['Situacao do voucher'].dropna().unique())

        return (
            [{'label': m, 'value': m} for m in meses],
            [{'label': r, 'value': r} for r in redes],
            [{'label': s, 'value': s} for s in situacoes],
            ultimo_mes,
            df.to_json(date_format='iso', orient='split')
        )
    except Exception as e:
        print(f"[ERRO] Falha ao processar planilha: {e}")
        return [], [], [], None, None

# CALLBACK PARA ATUALIZAR DASH
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
    Input('situacao-filter', 'value'),
)
def update_dashboard(json_data, mes, rede, situacoes):
    if not json_data:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, [], [], dash.no_update

    df = pd.read_json(io.StringIO(json_data), orient='split')
    df_filtrado = df.copy()

    if mes:
        df_filtrado = df_filtrado[df_filtrado['Mês'] == mes]
    if rede:
        df_filtrado = df_filtrado[df_filtrado['Nome da rede'] == rede]
    if situacoes:
        df_filtrado = df_filtrado[df_filtrado['Situacao do voucher'].isin(situacoes)]

    utilizados = df_filtrado[df_filtrado['Situacao do voucher'] == 'UTILIZADO']
    total_gerados = len(df_filtrado)
    total_utilizados = len(utilizados)
    valor_total = utilizados['Valor do voucher'].sum()
    ticket_medio = utilizados['Valor do voucher'].mean() if total_utilizados else 0
    taxa_conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0

    kpis = [
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("📦 Dispositivos Captados"),
                html.H4(f"{total_utilizados}")
            ])
        ], color="light"), md=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("💰 Captação Total"),
                html.H4(f"R$ {valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            ])
        ], color="light"), md=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("📊 Ticket Médio"),
                html.H4(f"R$ {ticket_medio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            ])
        ], color="light"), md=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("📈 Conversão"),
                html.H4(f"{taxa_conversao:.2f}%")
            ])
        ], color="light"), md=3),
    ]

    fig_gerados = px.histogram(df_filtrado, x='Criado em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.histogram(utilizados, x='Criado em', title='Vouchers Utilizados por Dia')

    fig_ticket = px.line(utilizados.groupby('Criado em')['Valor do voucher'].mean().reset_index(),
                         x='Criado em', y='Valor do voucher', title='Ticket Médio Diário')

    ranking = utilizados.groupby(['Nome do vendedor', 'Nome da filial', 'Nome da rede']) \
        .size().reset_index(name='Quantidade')
    ranking = ranking.sort_values(by='Quantidade', ascending=False).reset_index(drop=True)
    ranking['Ranking'] = ranking.index + 1
    cols = ['Ranking', 'Nome do vendedor', 'Nome da filial', 'Nome da rede', 'Quantidade']
    data = ranking[cols].to_dict('records')
    columns = [{'name': col, 'id': col} for col in cols]

    top_dispositivos = utilizados['Descrição'].value_counts().nlargest(10).reset_index()
    top_dispositivos.columns = ['Descrição', 'Quantidade']
    fig_dispositivos = px.bar(top_dispositivos, x='Descrição', y='Quantidade', title='Top Dispositivos')

    return kpis, fig_gerados, fig_utilizados, fig_ticket, data, columns, fig_dispositivos

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
