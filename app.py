import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from unidecode import unidecode
from datetime import datetime
from flask import send_file
from fpdf import FPDF

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Layout principal
app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={'textAlign': 'center'}),

    dbc.Row([
        dbc.Col(html.Button("📁 Importar Planilha Base", id="upload-button", n_clicks=0, className="btn btn-primary"), md=3),
        dcc.Upload(id="upload-data", style={"display": "none"}, multiple=False),
        dbc.Col(html.Button("🖨️ Exportar Resultados em PDF", id="export-pdf", n_clicks=0, className="btn btn-success"), md=3),
        dcc.Download(id="download-pdf")
    ], justify="center", className="my-3"),

    html.Div(id='error-upload', style={'color': 'red', 'textAlign': 'center', 'marginTop': 10}),
    html.Div(id='filtros'),
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos-mensais', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='graficos-rede', style={'marginTop': '40px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'})
])

# Atalho para disparar upload ao clicar no botão
@app.callback(Output('upload-data', 'style'), Input('upload-button', 'n_clicks'), prevent_initial_call=True)
def exibir_upload(n):
    return {"display": "block"}

@app.callback(
    Output('filtros', 'children'),
    Output('kpi-cards', 'children'),
    Output('graficos-mensais', 'children'),
    Output('graficos', 'children'),
    Output('graficos-rede', 'children'),
    Output('ranking-vendedores', 'children'),
    Output('error-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def processar_arquivo(contents, filename):
    if not contents:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        df.columns = [unidecode(col).strip().lower() for col in df.columns]

        obrigatorias = ['imei', 'criado em', 'valor do voucher', 'valor do dispositivo',
                        'situacao do voucher', 'nome do vendedor', 'nome da filial', 'nome da rede']
        for col in obrigatorias:
            if col not in df.columns:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes_curto'] = df['criado em'].dt.strftime('%b')
        df['mes'] = df['criado em'].dt.strftime('%b')
        df['mes_num'] = df['criado em'].dt.month
        df['dia'] = df['criado em'].dt.day.astype(str)

        app.df_original = df

        filtros_layout = dbc.Row([
            dbc.Col(dcc.Dropdown(id='filtro-mes',
                                 options=[{'label': m, 'value': m} for m in sorted(df['mes'].unique(), key=lambda x: datetime.strptime(x, "%b").month)],
                                 multi=True, placeholder="Mês"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-rede',
                                 options=[{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())],
                                 multi=True, placeholder="Rede"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-situacao',
                                 options=[{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())],
                                 multi=True, placeholder="Situação"), md=4)
        ], style={'marginTop': '20px'})

        return filtros_layout, gerar_kpis(df), gerar_graficos_mensais(df), gerar_graficos(df), gerar_graficos_rede(df), gerar_tabela(df), ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar: {str(e)}"

@app.callback(
    Output('kpi-cards', 'children', allow_duplicate=True),
    Output('graficos-mensais', 'children', allow_duplicate=True),
    Output('graficos', 'children', allow_duplicate=True),
    Output('graficos-rede', 'children', allow_duplicate=True),
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

    return gerar_kpis(df), gerar_graficos_mensais(df), gerar_graficos(df), gerar_graficos_rede(df), gerar_tabela(df)

def gerar_kpis(df):
    total_gerados = len(df)
    utilizados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    dispositivos = len(utilizados)
    captacao = utilizados['valor do dispositivo'].sum()
    ticket = captacao / dispositivos if dispositivos > 0 else 0
    conversao = (dispositivos / total_gerados * 100) if total_gerados > 0 else 0

    ultimo_mes = df['criado em'].dt.month.max()
    dias_ativos = df[df['criado em'].dt.month == ultimo_mes]['criado em'].dt.day.nunique()
    media_diaria = lambda valor: valor / dias_ativos if dias_ativos > 0 else 0
    projecao_mensal = lambda valor: media_diaria(valor) * 30

    def kpi_card(title, valor, daily=None, proj=None):
        sub = html.Div([
            html.Small(f"Média diária: {daily:,.0f}"),
            html.Br(),
            html.Small(f"Projeção do mês: {proj:,.0f}")
        ]) if daily is not None else None

        return dbc.Col(
            dbc.Card([
                html.H5(title),
                html.H3(valor),
                sub
            ], body=True, color="dark", inverse=True, style={"border": "2px solid lime"}), md=2
        )

    return dbc.Row([
        kpi_card("📊 Vouchers Gerados", f"{total_gerados}", media_diaria(total_gerados), projecao_mensal(total_gerados)),
        kpi_card("📦 Dispositivos Captados", f"{dispositivos}", media_diaria(dispositivos), projecao_mensal(dispositivos)),
        kpi_card("💰 Captação Total", f"R$ {captacao:,.2f}", media_diaria(captacao), projecao_mensal(captacao)),
        kpi_card("📍 Ticket Médio", f"R$ {ticket:,.2f}"),
        kpi_card("📈 Conversão", f"{conversao:.2f}%")
    ], justify='between', style={'marginBottom': 30})
def gerar_graficos_mensais(df):
    df = df.copy()
    df['mes_curto'] = df['criado em'].dt.strftime('%b')
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    meses_presentes = sorted(df['mes_curto'].unique(), key=lambda x: datetime.strptime(x, "%b").month)

    def fig_bar(dados, y, title):
        fig = px.bar(dados, x='mes_curto', y=y, text=y, title=title,
                     category_orders={'mes_curto': meses_presentes})
        fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', showlegend=False,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
            margin=dict(l=20, r=20, t=50, b=40)
        )
        return fig

    fig1 = fig_bar(df.groupby('mes_curto').size().reset_index(name='Qtd'), 'Qtd', "📅 Vouchers Gerados por Mês")
    fig2 = fig_bar(usados.groupby('mes_curto').size().reset_index(name='Qtd'), 'Qtd', "📅 Vouchers Utilizados por Mês")
    fig3 = fig_bar(usados.groupby('mes_curto')['valor do voucher'].mean().reset_index(name='Média'), 'Média', "💳 Ticket Médio por Mês")

    return dbc.Row([
        dbc.Col(dcc.Graph(figure=fig1), md=4),
        dbc.Col(dcc.Graph(figure=fig2), md=4),
        dbc.Col(dcc.Graph(figure=fig3), md=4),
    ])

def gerar_graficos(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    df['criado em'] = pd.to_datetime(df['criado em'])
    df['dia'] = df['criado em'].dt.day

    def make_fig(data, y_col, title, y_label):
        series = data.groupby('dia')[y_col].mean() if y_col != 'Qtd' else data.groupby('dia').size()
        serie_media_movel = series.rolling(window=3, min_periods=1).mean()
        media_simples = series.mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=series.index, y=series.values, mode='lines+markers+text',
                                 text=[f"{v:.0f}" for v in series.values], name=title,
                                 textposition='top center', line=dict(color='lime')))
        fig.add_trace(go.Scatter(x=serie_media_movel.index, y=serie_media_movel.values, mode='lines',
                                 name='Média Móvel', line=dict(color='lime', dash='dash')))
        fig.add_trace(go.Scatter(x=series.index, y=[media_simples]*len(series), mode='lines',
                                 name='Média Simples', line=dict(color='blue', dash='dot')))
        fig.update_layout(
            template='plotly_dark', title=title,
            plot_bgcolor='black', paper_bgcolor='black',
            xaxis=dict(title='Dia', tickmode='linear'),
            yaxis_title=y_label,
            margin=dict(t=30, b=40),
            showlegend=False
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
        return fig

    fig_gerados = make_fig(df, 'Qtd', "📅 Vouchers Gerados por Dia", 'Qtd')
    fig_utilizados = make_fig(usados, 'Qtd', "📅 Vouchers Utilizados por Dia", 'Qtd')
    fig_ticket = make_fig(usados, 'valor do voucher', "🎫 Ticket Médio Diário", 'Média')

    return dbc.Row([
        dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
        dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
        dbc.Col(dcc.Graph(figure=fig_ticket), md=4),
    ])
def gerar_graficos_rede(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    ordem_meses = sorted(df['mes_curto'].unique(), key=lambda x: datetime.strptime(x, "%b").month)

    base_kwargs = dict(x='nome da rede', y='Qtd', color='mes_curto', barmode='group', text='Qtd')

    df_gerados = df.groupby(['nome da rede', 'mes_curto']).size().reset_index(name='Qtd')
    df_gerados['mes_curto'] = pd.Categorical(df_gerados['mes_curto'], categories=ordem_meses, ordered=True)
    df_gerados = df_gerados.sort_values(['Qtd'], ascending=False)

    fig_gerados = px.bar(df_gerados, **base_kwargs, title="📊 Vouchers por Rede e Mês")
    fig_gerados.update_traces(texttemplate='%{text}', textposition='outside')
    fig_gerados.update_layout(
        margin=dict(t=30, b=100),
        xaxis_tickangle=-45,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False
    )

    df_usados = usados.groupby(['nome da rede', 'mes_curto']).size().reset_index(name='Qtd')
    df_usados['mes_curto'] = pd.Categorical(df_usados['mes_curto'], categories=ordem_meses, ordered=True)
    df_usados = df_usados.sort_values(['Qtd'], ascending=False)

    fig_usados = px.bar(df_usados, **base_kwargs, title="📦 Vouchers Utilizados por Rede e Mês")
    fig_usados.update_traces(texttemplate='%{text}', textposition='outside')
    fig_usados.update_layout(
        margin=dict(t=30, b=100),
        xaxis_tickangle=-45,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False
    )

    return html.Div([
        dcc.Graph(figure=fig_gerados),
        html.Div(style={'height': '30px'}),
        dcc.Graph(figure=fig_usados)
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

# 🚀 Execução
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
