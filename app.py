import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from unidecode import unidecode
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

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
    html.Div(id='graficos-mensal', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'})
])


@app.callback(
    Output('filtros', 'children'),
    Output('kpi-cards', 'children'),
    Output('graficos-mensal', 'children'),
    Output('graficos', 'children'),
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

        colunas_esperadas = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher', 'nome do vendedor', 'nome da filial', 'nome da rede', 'valor do dispositivo']
        for col in colunas_esperadas:
            if col not in df.columns:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes'] = df['criado em'].dt.strftime('%B')
        df['dia'] = df['criado em'].dt.day

        app.df_original = df

        filtros_layout = dbc.Row([
            dbc.Col(dcc.Dropdown(id='filtro-mes', options=[{'label': m, 'value': m} for m in sorted(df['mes'].dropna().unique())], multi=True, placeholder="Mês"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-rede', options=[{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())], multi=True, placeholder="Rede"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-situacao', options=[{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())], multi=True, placeholder="Situação do voucher"), md=4),
        ], style={'marginTop': '20px'})

        return filtros_layout, gerar_kpis(df), gerar_graficos_mensal(df), gerar_graficos(df), gerar_tabela(df), ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar arquivo: {str(e)}"


@app.callback(
    Output('kpi-cards', 'children', allow_duplicate=True),
    Output('graficos-mensal', 'children', allow_duplicate=True),
    Output('graficos', 'children', allow_duplicate=True),
    Output('ranking-vendedores', 'children', allow_duplicate=True),
    Input('filtro-mes', 'value'),
    Input('filtro-rede', 'value'),
    Input('filtro-situacao', 'value'),
    prevent_initial_call=True
)
def atualizar_dashboard(meses, redes, situacoes):
    df = app.df_original.copy()

    if meses:
        df = df[df['mes'].isin(meses)]
    if redes:
        df = df[df['nome da rede'].isin(redes)]
    if situacoes:
        df = df[df['situacao do voucher'].isin(situacoes)]

    return gerar_kpis(df), gerar_graficos_mensal(df), gerar_graficos(df), gerar_tabela(df)


def gerar_kpis(df):
    total_gerados = len(df)
    dispositivos = df[df['situacao do voucher'].str.lower() == 'utilizado'].shape[0]
    captacao = df[df['situacao do voucher'].str.lower() == 'utilizado']['valor do dispositivo'].sum()
    ticket = captacao / dispositivos if dispositivos > 0 else 0
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    conversao = len(usados) / total_gerados * 100 if total_gerados > 0 else 0

    estilo_card = {'border': '3px solid lime', 'box-shadow': '0 0 10px lime'}

    return dbc.Row([
        dbc.Col(dbc.Card([html.H5("📊 Vouchers Gerados"), html.H3(f"{total_gerados}")], body=True, color="dark", inverse=True, style=estilo_card), md=2),
        dbc.Col(dbc.Card([html.H5("📦 Dispositivos Captados"), html.H3(f"{dispositivos}")], body=True, color="dark", inverse=True, style=estilo_card), md=2),
        dbc.Col(dbc.Card([html.H5("💰 Captação Total"), html.H3(f"R$ {captacao:,.2f}")], body=True, color="dark", inverse=True, style=estilo_card), md=2),
        dbc.Col(dbc.Card([html.H5("🎯 Ticket Médio"), html.H3(f"R$ {ticket:,.2f}")], body=True, color="dark", inverse=True, style=estilo_card), md=2),
        dbc.Col(dbc.Card([html.H5("📈 Conversão"), html.H3(f"{conversao:.2f}%")], body=True, color="dark", inverse=True, style=estilo_card), md=2),
    ])


def gerar_graficos_mensal(df):
    df['mes_ordem'] = df['criado em'].dt.month
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    ticket = usados.groupby(df['criado em'].dt.strftime('%b'))['valor do voucher'].mean().reset_index(name='Média')

    fig1 = px.bar(df.groupby(df['criado em'].dt.strftime('%b')).size().reset_index(name='Qtd'),
                  x='criado em', y='Qtd', title='📆 Vouchers Gerados por Mês')

    fig2 = px.bar(usados.groupby(usados['criado em'].dt.strftime('%b')).size().reset_index(name='Qtd'),
                  x='criado em', y='Qtd', title='📆 Vouchers Utilizados por Mês')

    fig3 = px.bar(ticket, x='criado em', y='Média', title='💳 Ticket Médio por Mês')

    for fig in [fig1, fig2, fig3]:
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', showlegend=False)

    return dbc.Row([
        dbc.Col(dcc.Graph(figure=fig1), md=4),
        dbc.Col(dcc.Graph(figure=fig2), md=4),
        dbc.Col(dcc.Graph(figure=fig3), md=4),
    ])


def gerar_graficos(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']

    def base_trace(x, y, name, color):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers+text', name=name,
                                 line=dict(color=color), text=[f'{int(v):,}' if name != '🎫 Ticket Médio Diário' else f'{v:,.2f}' for v in y],
                                 textposition='top center'))
        return fig

    def plot_movel(fig, x, y):
        movel = pd.Series(y).rolling(3).mean()
        fig.add_trace(go.Scatter(x=x, y=movel, mode='lines', name='Média Móvel', line=dict(dash='dash', color='lime')))
        fig.add_hline(y=pd.Series(y).mean(), line_dash='dot', line_color='blue', annotation_text='Média')
        return fig

    fig_gerados = base_trace(df['dia'], df.groupby('dia').size(), "📅 Vouchers Gerados por Dia", 'lime')
    fig_utilizados = base_trace(usados['dia'], usados.groupby('dia').size(), "📅 Vouchers Utilizados por Dia", 'lime')
    fig_ticket = base_trace(usados['dia'], usados.groupby('dia')['valor do voucher'].mean(), "🎫 Ticket Médio Diário", 'lime')

    for fig in [fig_gerados, fig_utilizados, fig_ticket]:
        fig.update_layout(plot_bgcolor='black', paper_bgcolor='black',
                          font=dict(color='white'), showlegend=True, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))

    for fig, ydata in zip([fig_gerados, fig_utilizados, fig_ticket], [
        df.groupby('dia').size(), usados.groupby('dia').size(), usados.groupby('dia')['valor do voucher'].mean()
    ]):
        plot_movel(fig, ydata.index, ydata)

    return dbc.Row([
        dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
        dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
        dbc.Col(dcc.Graph(figure=fig_ticket), md=4),
    ])


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
