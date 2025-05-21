import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
import io
import base64
import unicodedata
import os

# App initialization
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Helpers
def normalizar_colunas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.normalize('NFKD')
        .str.encode('ascii', errors='ignore')
        .str.decode('utf-8')
    )
    return df

def parse_contents(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_excel(io.BytesIO(decoded))
        df = normalizar_colunas(df)  # << NORMALIZAÇÃO DAS COLUNAS AQUI
        return df
    except Exception as e:
        print(f'Erro ao processar arquivo: {e}')
        return None

# Layout
app.layout = dbc.Container([
    html.H2("Dashboard de Resultados", className="text-center mt-4"),
    
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            '📂 Arraste ou selecione o arquivo .xlsx'
        ]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
    
    dcc.Store(id='filtered-data'),
    
    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do voucher'), md=4),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col(html.Div(id='kpi-dispositivos'), md=3),
        dbc.Col(html.Div(id='kpi-captacao'), md=3),
        dbc.Col(html.Div(id='kpi-ticket-medio'), md=3),
        dbc.Col(html.Div(id='kpi-conversao'), md=3),
    ]),
    
    html.Hr(),
    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico-gerados'), md=4),
        dbc.Col(dcc.Graph(id='grafico-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='grafico-ticket'), md=4),
    ])
], fluid=True)

# Callbacks
@app.callback(
    Output('filtered-data', 'data'),
    Output('month-filter', 'options'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('month-filter', 'value'),
    Input('upload-data', 'contents')
)
def atualizar_dados(contents):
    if contents is None:
        return dash.no_update, [], [], [], None

    df = parse_contents(contents)
    if df is None:
        return dash.no_update, [], [], [], None

    if 'Criado em' not in df.columns:
        return dash.no_update, [], [], [], None

    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')

    meses = df['Criado em'].dt.strftime('%b').dropna().unique()
    redes = df['Nome da rede'].dropna().unique() if 'Nome da rede' in df.columns else []
    situacoes = df['Situacao do voucher'].dropna().unique() if 'Situacao do voucher' in df.columns else []

    return df.to_json(date_format='iso', orient='split'), \
           [{'label': m, 'value': m} for m in sorted(meses)], \
           [{'label': r, 'value': r} for r in sorted(redes)], \
           [{'label': s, 'value': s} for s in sorted(situacoes)], \
           sorted(meses)[-1] if len(meses) > 0 else None


@app.callback(
    Output('kpi-dispositivos', 'children'),
    Output('kpi-captacao', 'children'),
    Output('kpi-ticket-medio', 'children'),
    Output('kpi-conversao', 'children'),
    Output('grafico-gerados', 'figure'),
    Output('grafico-utilizados', 'figure'),
    Output('grafico-ticket', 'figure'),
    Input('filtered-data', 'data'),
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value'),
)
def atualizar_dashboard(json_data, mes, rede, situacao):
    if json_data is None:
        return [dash.no_update] * 7

    df = pd.read_json(json_data, orient='split')

    # Filtros
    if mes:
        df = df[df['Criado em'].dt.strftime('%b') == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacao:
        df = df[df['Situacao do voucher'] == situacao]

    total_dispositivos = df.shape[0]
    captacao = df['Valor do voucher'].sum()
    utilizados = df[df['Situacao do voucher'] == 'UTILIZADO']
    ticket = utilizados['Valor do voucher'].mean() if not utilizados.empty else 0
    conversao = (utilizados.shape[0] / total_dispositivos * 100) if total_dispositivos > 0 else 0

    kpi_style = {
        "backgroundColor": "#1e1e1e",
        "border": "2px solid #00FFFF",
        "padding": "15px",
        "borderRadius": "8px",
        "color": "white"
    }

    kpi1 = html.Div([
        html.H5("📦 Dispositivos Captados"),
        html.H4(f"{total_dispositivos}")
    ], style=kpi_style)

    kpi2 = html.Div([
        html.H5("💰 Captação Total"),
        html.H4(f"R$ {captacao:,.2f}")
    ], style=kpi_style)

    kpi3 = html.Div([
        html.H5("📊 Ticket Médio"),
        html.H4(f"R$ {ticket:,.2f}")
    ], style=kpi_style)

    kpi4 = html.Div([
        html.H5("📈 Conversão"),
        html.H4(f"{conversao:.2f}%")
    ], style=kpi_style)

    # Gráficos
    fig_gerados = px.line(
        df.groupby(df['Criado em'].dt.date).size().reset_index(name='Qtd'),
        x='Criado em', y='Qtd', markers=True,
        title="Vouchers Gerados por Dia"
    )
    fig_utilizados = px.line(
        utilizados.groupby(utilizados['Criado em'].dt.date).size().reset_index(name='Qtd'),
        x='Criado em', y='Qtd', markers=True,
        title="Vouchers Utilizados por Dia"
    )
    fig_ticket = px.line(
        utilizados.groupby(utilizados['Criado em'].dt.date)['Valor do voucher'].mean().reset_index(),
        x='Criado em', y='Valor do voucher', markers=True,
        title="Ticket Médio Diário"
    )

    for fig in [fig_gerados, fig_utilizados, fig_ticket]:
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=40), template='plotly_white')
        fig.update_xaxes(title_text='Data', tickformat="%d %b")

    return kpi1, kpi2, kpi3, kpi4, fig_gerados, fig_utilizados, fig_ticket

# Run
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
