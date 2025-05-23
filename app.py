# ... (importações mantidas)
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

app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={'textAlign': 'center'}),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Arraste ou selecione o arquivo .xlsx']),
        style={'width': '100%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '1px',
               'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center'},
        multiple=False
    ),
    html.Div(id='error-upload', style={'color': 'red', 'textAlign': 'center', 'marginTop': 10}),
    html.Div(id='filtros'),
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos-mes', style={'marginTop': '20px'}),
    html.Div(id='graficos-dia', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'})
])

@app.callback(
    Output('filtros', 'children'),
    Output('kpi-cards', 'children'),
    Output('graficos-mes', 'children'),
    Output('graficos-dia', 'children'),
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
        required = ['imei', 'criado em', 'valor do voucher', 'valor do dispositivo', 'situacao do voucher',
                    'nome do vendedor', 'nome da filial', 'nome da rede']
        for col in required:
            if col not in df.columns:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes'] = df['criado em'].dt.month_name().str[:3]
        df['dia'] = df['criado em'].dt.day
        app.df_original = df

        filtros = dbc.Row([
            dbc.Col(dcc.Dropdown(id='filtro-mes',
                                 options=[{'label': m, 'value': m} for m in sorted(df['mes'].dropna().unique(), key=lambda x: datetime.strptime(x, '%b').month)],
                                 multi=True, placeholder="Mês"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-rede',
                                 options=[{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())],
                                 multi=True, placeholder="Rede"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-situacao',
                                 options=[{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())],
                                 multi=True, placeholder="Situação do voucher"), md=4),
        ])

        return filtros, gerar_kpis(df), gerar_graficos_mes(df), gerar_graficos_dia(df), gerar_tabela(df), ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar: {str(e)}"

@app.callback(
    Output('kpi-cards', 'children', allow_duplicate=True),
    Output('graficos-mes', 'children', allow_duplicate=True),
    Output('graficos-dia', 'children', allow_duplicate=True),
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
    return gerar_kpis(df), gerar_graficos_mes(df), gerar_graficos_dia(df), gerar_tabela(df)

# 🧠 Funções de Geração
def gerar_kpis(df):
    total = len(df)
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    captados = usados.shape[0]
    captacao = usados['valor do dispositivo'].sum()
    ticket = captacao / captados if captados else 0
    conversao = (captados / total * 100) if total else 0

    def kpi_card(titulo, valor):
        return dbc.Col(dbc.Card([
            html.H5(titulo),
            html.H3(valor)
        ], body=True, color="dark", inverse=True, style={'border': '3px solid lime'}), md=2)

    return dbc.Row([
        kpi_card("📊 Vouchers Gerados", f"{total}"),
        kpi_card("📦 Dispositivos Captados", f"{captados}"),
        kpi_card("💰 Captação Total", f"R$ {captacao:,.2f}"),
        kpi_card("🎯 Ticket Médio", f"R$ {ticket:,.2f}"),
        kpi_card("📈 Conversão", f"{conversao:.2f}%"),
    ], justify='center')

def gerar_graficos_mes(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    ordem_meses = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def grafico_bar(df, y, titulo, ytitle):
        df['mes'] = pd.Categorical(df['mes'], categories=ordem_meses, ordered=True)
        resumo = df.groupby('mes')[y].agg('mean' if y == 'valor do voucher' else 'count').reindex(ordem_meses).dropna()
        fig = go.Figure(go.Bar(x=resumo.index, y=resumo.values, marker_color='royalblue', text=resumo.values, textposition='outside'))
        fig.update_layout(paper_bgcolor='white', plot_bgcolor='white', title=titulo, margin=dict(t=30), height=300)
        fig.update_yaxes(title=ytitle)
        return dcc.Graph(figure=fig)

    return dbc.Row([
        dbc.Col(grafico_bar(df, 'valor do voucher', "📅 Vouchers Gerados por Mês", "Qtd"), md=4),
        dbc.Col(grafico_bar(usados, 'valor do voucher', "📅 Vouchers Utilizados por Mês", "Qtd"), md=4),
        dbc.Col(grafico_bar(usados, 'valor do voucher', "📈 Ticket Médio por Mês", "Média"), md=4),
    ])

def gerar_graficos_dia(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']

    def plot_line(df, y, nome, titulo):
        df_group = df.groupby('dia')[y].agg('count' if y != 'valor do voucher' else 'mean')
        media = df_group.mean()
        media_movel = df_group.rolling(3, min_periods=1).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_group.index, y=df_group, name=nome, mode='lines+markers+text', text=df_group.round(2), textposition='top center', line=dict(color='lime')))
        fig.add_trace(go.Scatter(x=media_movel.index, y=media_movel, name="Média Móvel", mode='lines', line=dict(dash='dash', color='lime')))
        fig.add_hline(y=media, line_dash='dot', line_color='blue', annotation_text="Média", annotation_position="top left")
        fig.update_layout(paper_bgcolor='black', plot_bgcolor='black', font_color='white', title=titulo, height=350)
        return dcc.Graph(figure=fig)

    return dbc.Row([
        dbc.Col(plot_line(df, 'valor do voucher', "📅 Vouchers Gerados por Dia", "📅 Vouchers Gerados por Dia"), md=4),
        dbc.Col(plot_line(usados, 'valor do voucher', "📅 Vouchers Utilizados por Dia", "📅 Vouchers Utilizados por Dia"), md=4),
        dbc.Col(plot_line(usados, 'valor do voucher', "🎫 Ticket Médio Diário", "🎫 Ticket Médio Diário"), md=4),
    ])

def gerar_tabela(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    ranking = usados.groupby(['nome do vendedor', 'nome da filial', 'nome da rede']).size().reset_index(name='Qtd')
    top10 = ranking.sort_values(by='Qtd', ascending=False).head(10)
    return html.Div([
        html.H5("🏆 Top 10 Vendedores por Volume de Vouchers"),
        dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in top10.columns],
            data=top10.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            style_header={'backgroundColor': 'black', 'color': 'white'}
        )
    ])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
