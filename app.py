import os
import base64
import io
from datetime import datetime
from unidecode import unidecode  # <== precisa estar instalado

import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc  # <== define 'dbc'
import plotly.express as px  # <== define 'px'



# Inicializar app
app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Layout
app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={'textAlign': 'center', 'marginBottom': 10}),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            '📁 Arraste ou selecione o arquivo .xlsx'
        ]),
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
    html.Div(id='erro-upload', style={'color': 'red', 'textAlign': 'center'}),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='month-filter', placeholder="Mês"), width=2),
        dbc.Col(dcc.Dropdown(id='rede-filter', placeholder="Nome da rede", multi=True), width=4),
        dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder="Situação do voucher", multi=True), width=3),
    ], style={"marginBottom": 20}),

    dcc.Store(id='filtered-data'),

    dbc.Row([
        dbc.Col(html.Div(id='kpi-vouchers-gerados', className='card-kpi'), width=2),
        dbc.Col(html.Div(id='kpi-dispositivos', className='card-kpi'), width=2),
        dbc.Col(html.Div(id='kpi-captacao', className='card-kpi'), width=2),
        dbc.Col(html.Div(id='kpi-ticket-medio', className='card-kpi'), width=2),
        dbc.Col(html.Div(id='kpi-conversao', className='card-kpi'), width=2),
    ], style={'marginBottom': 30, 'marginTop': 10}),

    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico-gerados'), width=4),
        dbc.Col(dcc.Graph(id='grafico-utilizados'), width=4),
        dbc.Col(dcc.Graph(id='grafico-ticket'), width=4),
    ]),

    html.Hr(),

    dbc.Row([
        dbc.Col([
            html.H5("Ranking Vendedores", style={'marginBottom': 10}),
            dash_table.DataTable(
                id='tabela-vendedores',
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'fontSize': 12},
                style_header={'backgroundColor': 'black', 'color': 'white'},
                page_size=20
            )
        ], width=6),

        dbc.Col([
            html.H5("Top Dispositivos", style={'marginBottom': 10}),
            dcc.Graph(id='grafico-top-dispositivos')
        ], width=6)
    ])
])

# CSS (estilo dos cards)
app.clientside_callback(
    """
    function(_) {
        const style = document.createElement('style');
        style.innerHTML = `
        .card-kpi {
            background-color: #1e1e1e;
            padding: 15px;
            border-radius: 8px;
            color: white;
            border: 2px solid #00e6d2;
            text-align: left;
        }
        `;
        document.head.appendChild(style);
        return '';
    }
    """,
    Output('erro-upload', 'children'),
    Input('upload-data', 'contents')
)
from dash.exceptions import PreventUpdate
from unidecode import unidecode

@app.callback(
    Output('month-filter', 'options'),
    Output('month-filter', 'value'),
    Output('rede-filter', 'options'),
    Output('situacao-filter', 'options'),
    Output('filtered-data', 'data'),
    Output('erro-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def processar_upload(contents, filename):
    if contents is None:
        raise PreventUpdate

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        df = pd.read_excel(io.BytesIO(decoded))

        # Padroniza nomes das colunas
        df.columns = [unidecode(col.strip().lower().replace(" ", "_")) for col in df.columns]

        if 'criado_em' not in df.columns:
            return [], None, [], [], None, "Erro: coluna 'Criado em' não encontrada"

        df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
        df = df[df['criado_em'].notna()]  # remove linhas com data inválida

        df['mes'] = df['criado_em'].dt.strftime('%b')

        meses = sorted(df['mes'].dropna().unique(), key=lambda m: datetime.strptime(m, '%b').month)
        redes = sorted(df['nome_da_rede'].dropna().unique()) if 'nome_da_rede' in df.columns else []
        situacoes = sorted(df['situacao_do_voucher'].dropna().unique()) if 'situacao_do_voucher' in df.columns else []

        latest_month = meses[-1] if meses else None

        return (
            [{'label': m, 'value': m} for m in meses],
            latest_month,
            [{'label': r, 'value': r} for r in redes],
            [{'label': s, 'value': s} for s in situacoes],
            df.to_json(date_format='iso', orient='split'),
            ""
        )

    except Exception as e:
        return [], None, [], [], None, f"Erro ao processar o arquivo: {str(e)}"

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
    Input('month-filter', 'value'),
    Input('rede-filter', 'value'),
    Input('situacao-filter', 'value'),
    Input('filtered-data', 'data'),
)
def atualizar_dashboard(mes, rede, situacao, json_data):
    if json_data is None:
        raise dash.exceptions.PreventUpdate

    df = pd.read_json(json_data, orient='split')

    # Garantir datetime
    df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
    df = df[df['criado_em'].notna()]

    # Filtros
    if mes:
        df = df[df['criado_em'].dt.strftime('%b') == mes]
    if rede:
        df = df[df['nome_da_rede'].isin(rede)]
    if situacao:
        df = df[df['situacao_do_voucher'].isin(situacao)]

    # KPIs
    total_gerados = len(df)
    utilizados = df[df['situacao_do_voucher'] == 'UTILIZADO']
    total_utilizados = len(utilizados)
    captacao = utilizados['valor_do_voucher'].sum() if 'valor_do_voucher' in utilizados else 0
    ticket_medio = utilizados['valor_do_voucher'].mean() if total_utilizados else 0
    conversao = (total_utilizados / total_gerados * 100) if total_gerados else 0

    def kpi_card(label, valor):
        return html.Div([
            html.Small(label, style={"fontWeight": "bold"}),
            html.H4(valor)
        ])

    k1 = kpi_card("📄 Vouchers Gerados", f"{total_gerados}")
    k2 = kpi_card("📦 Dispositivos Captados", f"{total_utilizados}")
    k3 = kpi_card("💰 Captação Total", f"R$ {captacao:,.2f}".replace(".", "X").replace(",", ".").replace("X", ","))
    k4 = kpi_card("📊 Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(".", "X").replace(",", ".").replace("X", ","))
    k5 = kpi_card("📈 Conversão", f"{conversao:.2f}%")

    # Gráficos
    fig_gerados = px.line(
        df.groupby(df['criado_em'].dt.date).size().reset_index(name='qtd'),
        x='criado_em', y='qtd', title='Vouchers Gerados por Dia'
    )
    fig_utilizados = px.line(
        utilizados.groupby(utilizados['criado_em'].dt.date).size().reset_index(name='qtd'),
        x='criado_em', y='qtd', title='Vouchers Utilizados por Dia'
    )
    fig_ticket = px.line(
        utilizados.groupby(utilizados['criado_em'].dt.date)['valor_do_voucher'].mean().reset_index(),
        x='criado_em', y='valor_do_voucher', title='Ticket Médio Diário'
    )

    for fig in [fig_gerados, fig_utilizados, fig_ticket]:
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=30), height=300, template='plotly_white')
        fig.update_traces(mode="lines+markers")
        fig.update_xaxes(tickformat="%d/%b", title="Data")
        fig.update_yaxes(title="")

    # Tabela de Vendedores
    if 'nome_do_vendedor' in utilizados.columns:
        rank_df = utilizados.groupby(
            ['nome_do_vendedor', 'nome_da_filial', 'nome_da_rede']
        ).size().reset_index(name='Quantidade')

        rank_df['Ranking'] = rank_df['Quantidade'].rank(method='first', ascending=False).astype(int)
        rank_df = rank_df.sort_values(by='Ranking')
        dados = rank_df.to_dict('records')
        colunas = [{'name': i.replace("_", " ").title(), 'id': i} for i in rank_df.columns]
    else:
        dados, colunas = [], []

    # Top Dispositivos
    if 'descricao' in df.columns:
        top_dispositivos = df['descricao'].value_counts().nlargest(10).reset_index()
        top_dispositivos.columns = ['Descricao', 'Quantidade']
        fig_dispositivos = px.bar(top_dispositivos, x='Descricao', y='Quantidade', title="Top Dispositivos")
        fig_dispositivos.update_traces(text='Quantidade', textposition='outside')
        fig_dispositivos.update_layout(margin=dict(t=40), height=300)
    else:
        fig_dispositivos = px.bar(title="Dispositivos não encontrados")

    return k1, k2, k3, k4, k5, fig_gerados, fig_utilizados, fig_ticket, dados, colunas, fig_dispositivos

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=True, host="0.0.0.0", port=port)
