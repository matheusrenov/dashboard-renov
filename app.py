import dash
from dash import Dash, dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import base64
import io
from datetime import datetime

# App inicial
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Layout base
app.layout = dbc.Container([
    html.H2("Dashboard de Resultados", style={"textAlign": "center", "marginTop": "20px"}),
    
    # Upload
    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center',
            'marginBottom': '10px'
        },
        multiple=False
    ),

    html.Div(id='upload-error', style={'color': 'red', 'textAlign': 'center'}),

    # Filtros
    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder='Mês'), md=4),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder='Nome da rede'), md=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder='Situação do voucher'), md=4),
    ], style={"marginTop": "10px"}),

    dcc.Store(id='filtered-data'),

    # KPIs
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),

    # Gráficos
    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico-gerados'), md=4),
        dbc.Col(dcc.Graph(id='grafico-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='grafico-ticket'), md=4)
    ]),

    # Tabela e ranking
    dbc.Row([
        dbc.Col(dash_table.DataTable(id='tabela-vendedores', style_table={'overflowX': 'auto'}), md=6),
        dbc.Col(dcc.Graph(id='grafico-top-dispositivos'), md=6)
    ])
], fluid=True)

# Callback para carregar o arquivo e preparar os filtros
@app.callback(
    Output('month-filter', 'options'),
    Output('month-filter', 'value'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('filtered-data', 'data'),
    Output('upload-error', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def carregar_arquivo(contents, filename):
    if contents is None:
        return [], None, [], [], None, None

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_excel(io.BytesIO(decoded))

        # Padroniza colunas
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        # Renomeia colunas esperadas
        renomear = {
            'criado_em': 'criado_em',
            'situação_do_voucher': 'situacao_do_voucher',
            'situação_do_voucher': 'situacao_do_voucher',
            'nome_da_rede': 'nome_da_rede',
        }

        for key in renomear:
            if key in df.columns:
                df.rename(columns={key: renomear[key]}, inplace=True)

        # Converte datas
        df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')

        # Filtros
        df['mes'] = df['criado_em'].dt.strftime('%b')  # abreviação
        meses = sorted(df['mes'].dropna().unique(), key=lambda x: datetime.strptime(x, "%b").month)
        redes = sorted(df['nome_da_rede'].dropna().unique()) if 'nome_da_rede' in df else []
        situacoes = sorted(df['situacao_do_voucher'].dropna().unique()) if 'situacao_do_voucher' in df else []

        ultimo_mes = meses[-1] if meses else None

        return (
            [{'label': m, 'value': m} for m in meses],
            ultimo_mes,
            [{'label': r, 'value': r} for r in redes],
            [{'label': s, 'value': s} for s in situacoes],
            df.to_dict('records'),
            None
        )
    except Exception as e:
        return [], None, [], [], None, f"Erro ao processar arquivo: {str(e)}"

# Callback principal para atualizar dashboard
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
def atualizar_dashboard(mes, rede, situacao, data):
    if data is None:
        return [html.Div("Nenhum dado carregado.")], {}, {}, {}, [], [], {}

    df = pd.DataFrame(data)

    # Filtros
    if mes:
        df = df[df['criado_em'].dt.strftime('%b') == mes]
    if rede:
        df = df[df['nome_da_rede'] == rede]
    if situacao:
        df = df[df['situacao_do_voucher'] == situacao]

    # KPIs
    total_vouchers = len(df)
    dispositivos = df['dispositivo'].nunique() if 'dispositivo' in df else 0
    captacao = df['valor_do_voucher'].sum() if 'valor_do_voucher' in df else 0
    ticket_medio = df['valor_do_voucher'].mean() if 'valor_do_voucher' in df else 0
    usados = df[df['situacao_do_voucher'] == 'UTILIZADO'] if 'situacao_do_voucher' in df else pd.DataFrame()
    conversao = (len(usados) / total_vouchers) * 100 if total_vouchers > 0 else 0

    kpis = dbc.Row([
        dbc.Col(html.Div([
            html.H5("📄 Vouchers Gerados", style={'color': 'white'}),
            html.H3(f"{total_vouchers}", style={'color': 'white'})
        ], className="p-3", style={"background": "#1e1e1e", "border": "2px solid turquoise", "borderRadius": "10px"}), md=3),

        dbc.Col(html.Div([
            html.H5("📦 Dispositivos Captados", style={'color': 'white'}),
            html.H3(f"{dispositivos}", style={'color': 'white'})
        ], className="p-3", style={"background": "#1e1e1e", "border": "2px solid turquoise", "borderRadius": "10px"}), md=3),

        dbc.Col(html.Div([
            html.H5("💰 Captação Total", style={'color': 'white'}),
            html.H3(f"R$ {captacao:,.2f}", style={'color': 'white'})
        ], className="p-3", style={"background": "#1e1e1e", "border": "2px solid turquoise", "borderRadius": "10px"}), md=3),

        dbc.Col(html.Div([
            html.H5("📊 Ticket Médio", style={'color': 'white'}),
            html.H3(f"R$ {ticket_medio:,.2f}", style={'color': 'white'})
        ], className="p-3", style={"background": "#1e1e1e", "border": "2px solid turquoise", "borderRadius": "10px"}), md=3),

        dbc.Col(html.Div([
            html.H5("📈 Conversão", style={'color': 'white'}),
            html.H3(f"{conversao:.2f}%", style={'color': 'white'})
        ], className="p-3", style={"background": "#1e1e1e", "border": "2px solid turquoise", "borderRadius": "10px"}), md=3),
    ])

    # Gráficos
    fig_gerados = px.line(df, x='criado_em', title='Vouchers Gerados por Dia')
    fig_utilizados = px.line(df[df['situacao_do_voucher'] == 'UTILIZADO'], x='criado_em', title='Vouchers Utilizados por Dia') if 'situacao_do_voucher' in df else px.line(title='Sem dados de utilização')
    fig_ticket = px.line(df, x='criado_em', y='valor_do_voucher', title='Ticket Médio Diário') if 'valor_do_voucher' in df else px.line(title='Sem dados de ticket')

    # Ranking vendedores
    if 'nome_do_vendedor' in df:
        top_vend = df[df['situacao_do_voucher'] == 'UTILIZADO'].groupby(['nome_do_vendedor', 'nome_da_filial']).size().reset_index(name='qtd')
        top_vend = top_vend.sort_values(by='qtd', ascending=False).reset_index(drop=True)
        top_vend.insert(0, 'Ranking', top_vend.index + 1)
        tabela_vendedores = top_vend.to_dict('records')
        colunas_vendedores = [{"name": i.replace("_", " ").title(), "id": i} for i in top_vend.columns]
    else:
        tabela_vendedores, colunas_vendedores = [], []

    # Top dispositivos
    fig_dispositivos = px.bar(df, x='descricao', title='Top Dispositivos') if 'descricao' in df else px.bar(title='Sem dispositivos')

    return kpis, fig_gerados, fig_utilizados, fig_ticket, tabela_vendedores, colunas_vendedores, fig_dispositivos

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
