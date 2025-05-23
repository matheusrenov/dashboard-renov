import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from unidecode import unidecode
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Layout
app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={'textAlign': 'center'}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center'
        },
        multiple=False
    ),
    html.Div(id='error-upload', style={'color': 'red', 'textAlign': 'center', 'marginTop': 10}),
    html.Div(id='filtros'),
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos-mensais', style={'marginTop': '20px'}),
    html.Div(id='graficos-diarios', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'})
])

# Upload
@app.callback(
    Output('filtros', 'children'),
    Output('kpi-cards', 'children'),
    Output('graficos-mensais', 'children'),
    Output('graficos-diarios', 'children'),
    Output('ranking-vendedores', 'children'),
    Output('error-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def processar_arquivo(contents, filename):
    if not contents:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        df.columns = [unidecode(col).strip().lower() for col in df.columns]

        colunas_necessarias = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher', 'nome do vendedor', 'nome da filial', 'nome da rede', 'valor do dispositivo']
        for col in colunas_necessarias:
            if col not in df.columns:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes'] = df['criado em'].dt.strftime('%b')
        df['dia'] = df['criado em'].dt.day
        df['mes_num'] = df['criado em'].dt.month

        app.df_original = df.copy()

        filtros = dbc.Row([
            dbc.Col(dcc.Dropdown(id='filtro-mes', options=[{'label': m, 'value': m} for m in sorted(df['mes'].unique(), key=lambda x: datetime.strptime(x, "%b").month)], multi=True, placeholder="Mês"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-rede', options=[{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())], multi=True, placeholder="Rede"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-situacao', options=[{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())], multi=True, placeholder="Situação do voucher"), md=4),
        ])

        return filtros, gerar_kpis(df), gerar_graficos_mensais(df), gerar_graficos_diarios(df), gerar_tabela(df), ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar: {str(e)}"

# Callback filtros
@app.callback(
    Output('kpi-cards', 'children', allow_duplicate=True),
    Output('graficos-mensais', 'children', allow_duplicate=True),
    Output('graficos-diarios', 'children', allow_duplicate=True),
    Output('ranking-vendedores', 'children', allow_duplicate=True),
    Input('filtro-mes', 'value'),
    Input('filtro-rede', 'value'),
    Input('filtro-situacao', 'value'),
    prevent_initial_call=True
)
def atualizar(meses, redes, situacoes):
    df = app.df_original.copy()
    if meses:
        df = df[df['mes'].isin(meses)]
    if redes:
        df = df[df['nome da rede'].isin(redes)]
    if situacoes:
        df = df[df['situacao do voucher'].isin(situacoes)]

    return gerar_kpis(df), gerar_graficos_mensais(df), gerar_graficos_diarios(df), gerar_tabela(df)

# KPIs
def gerar_kpis(df):
    total_gerados = len(df)
    utilizados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    dispositivos = len(utilizados)
    captacao = utilizados['valor do dispositivo'].sum()
    ticket = captacao / dispositivos if dispositivos > 0 else 0
    conversao = (dispositivos / total_gerados) * 100 if total_gerados > 0 else 0

    card_style = {'textAlign': 'center', 'boxShadow': '0 0 5px 2px limegreen'}

    return dbc.Row([
        dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(f"{total_gerados}")], body=True, color="dark", inverse=True, style=card_style), md=2),
        dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(f"{dispositivos}")], body=True, color="dark", inverse=True, style=card_style), md=2),
        dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")], body=True, color="dark", inverse=True, style=card_style), md=2),
        dbc.Col(dbc.Card([html.H5("🎯 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")], body=True, color="dark", inverse=True, style=card_style), md=2),
        dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")], body=True, color="dark", inverse=True, style=card_style), md=2),
    ], justify='center')

# GRÁFICOS MENSAIS
def gerar_graficos_mensais(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']

    def bar_chart(data, y, title):
        fig = go.Figure(data=[
            go.Bar(x=data['mes'], y=data[y], text=data[y], textposition='outside', marker_color='cornflowerblue')
        ])
        fig.update_layout(title=title, xaxis_title="criado em", yaxis_title=y, plot_bgcolor='white')
        return dcc.Graph(figure=fig)

    mensal = df.groupby(['mes', 'mes_num']).agg({
        'valor do voucher': 'count',
        'criado em': 'first'
    }).reset_index().sort_values('mes_num')
    mensal_usados = usados.groupby(['mes', 'mes_num']).agg({'valor do voucher': 'count'}).reset_index().sort_values('mes_num')
    mensal_ticket = usados.groupby(['mes', 'mes_num'])['valor do voucher'].mean().reset_index().sort_values('mes_num')

    return dbc.Row([
        dbc.Col(bar_chart(mensal, 'valor do voucher', "📅 Vouchers Gerados por Mês"), md=4),
        dbc.Col(bar_chart(mensal_usados, 'valor do voucher', "📅 Vouchers Utilizados por Mês"), md=4),
        dbc.Col(bar_chart(mensal_ticket, 'valor do voucher', "🎫 Ticket Médio por Mês"), md=4),
    ])

# GRÁFICOS DIÁRIOS
def gerar_graficos_diarios(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']

    def line_with_avg(series, title, yaxis):
        daily = series.groupby(series.index.day).mean()
        media_movel = daily.rolling(5).mean()
        media_simples = daily.mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily.index, y=daily, mode='lines+markers+text',
                                 name=title, text=[f"{y:.0f}" for y in daily],
                                 textposition='top center', line=dict(color='lime')))
        fig.add_trace(go.Scatter(x=media_movel.index, y=media_movel,
                                 mode='lines', name='Média Móvel', line=dict(color='lime', dash='dash')))
        fig.add_trace(go.Scatter(x=daily.index, y=[media_simples]*len(daily),
                                 mode='lines', name='Média', line=dict(color='blue', dash='dot')))

        fig.update_layout(title=title, plot_bgcolor='black', paper_bgcolor='black',
                          font=dict(color='white'), xaxis_title="dia", yaxis_title=yaxis,
                          showlegend=True)
        return dcc.Graph(figure=fig)

    df.set_index('criado em', inplace=True)
    fig1 = line_with_avg(df.groupby(df.index)['valor do voucher'].count(), "📅 Vouchers Gerados por Dia", "Qtd")
    fig2 = line_with_avg(usados.groupby(usados.index)['valor do voucher'].count(), "📅 Vouchers Utilizados por Dia", "Qtd")
    fig3 = line_with_avg(usados.groupby(usados.index)['valor do voucher'].mean(), "🎫 Ticket Médio Diário", "Média")

    return dbc.Row([dbc.Col(fig1, md=4), dbc.Col(fig2, md=4), dbc.Col(fig3, md=4)])

# TABELA
def gerar_tabela(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    ranking = usados.groupby(['nome do vendedor', 'nome da filial', 'nome da rede']).size().reset_index(name='Qtd')
    ranking = ranking.sort_values(by='Qtd', ascending=False).head(10)

    return html.Div([
        html.H5("🏆 Top 10 Vendedores por Volume de Vouchers"),
        dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ranking.columns],
            data=ranking.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            style_header={'backgroundColor': 'black', 'color': 'white'}
        )
    ])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
