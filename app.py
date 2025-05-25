import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from unidecode import unidecode

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# ========================
# 💠 LAYOUT
# ========================
app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={'textAlign': 'center'}),

    html.Div([
        dcc.Upload(
            id="upload-data",
            children=html.Button("📁 Importar Planilha Base", className="btn btn-primary"),
            accept=".xlsx",
            multiple=False
        ),
        html.Button("🖨️ Exportar Resultados em PDF", id="export-pdf", n_clicks=0, className="btn btn-success", style={"marginLeft": "10px"})
    ], style={"textAlign": "center", "marginTop": "20px", "marginBottom": "20px"}),

    dcc.Download(id="download-pdf"),

    html.Div(id='error-upload', style={'color': 'red', 'textAlign': 'center'}),
    html.Div(id='filtros'),
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos-mensais', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='graficos-rede', style={'marginTop': '40px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'}),
])

# ========================
# 📥 PROCESSAR UPLOAD
# ========================
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

        df.columns = [unidecode(c).strip().lower() for c in df.columns]

        obrigatorias = ['imei', 'criado em', 'valor do voucher', 'valor do dispositivo',
                        'situacao do voucher', 'nome do vendedor', 'nome da filial', 'nome da rede']
        for col in obrigatorias:
            if col not in df.columns:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes_curto'] = df['criado em'].dt.strftime('%b')
        df['mes_num'] = df['criado em'].dt.month
        df['mes'] = df['criado em'].dt.strftime('%b')
        df['dia'] = df['criado em'].dt.day.astype(int)

        app.df_original = df

        filtros = dbc.Row([
            dbc.Col(dcc.Dropdown(
                id='filtro-mes',
                options=[{'label': m, 'value': m} for m in sorted(df['mes'].unique(), key=lambda x: datetime.strptime(x, "%b").month)],
                multi=True,
                placeholder="Mês"
            ), md=4),
            dbc.Col(dcc.Dropdown(
                id='filtro-rede',
                options=[{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())],
                multi=True,
                placeholder="Rede"
            ), md=4),
            dbc.Col(dcc.Dropdown(
                id='filtro-situacao',
                options=[{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())],
                multi=True,
                placeholder="Situação do Voucher"
            ), md=4),
        ], style={'marginTop': '20px'})

        return filtros, gerar_kpis(df), gerar_graficos_mensais(df), gerar_graficos(df), gerar_graficos_rede(df), gerar_tabela(df), ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar: {str(e)}"

# ========================
# 🔄 ATUALIZAÇÕES
# ========================
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

# ========================
# 🧠 FUNÇÕES AUXILIARES
# ========================
def gerar_kpis(df):
    total = len(df)
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    captados = len(usados)
    valor_total = usados['valor do dispositivo'].sum()
    ticket = valor_total / captados if captados > 0 else 0
    conversao = captados / total * 100 if total > 0 else 0

    mes_vigente = df['criado em'].dt.month.max()
    dias = df[df['criado em'].dt.month == mes_vigente]['criado em'].dt.day.nunique()
    media = lambda v: v / dias if dias > 0 else 0
    proj = lambda v: media(v) * 30

    def card(titulo, valor, media_dia=None, projecao=None):
        children = [html.H5(titulo), html.H3(valor)]
        if media_dia is not None:
            children.append(html.Small(f"Média diária: {media_dia:,.0f}"))
            children.append(html.Br())
            children.append(html.Small(f"Projeção do mês: {projecao:,.0f}"))
        return dbc.Col(dbc.Card(children, body=True, color="dark", inverse=True, style={"border": "2px solid lime"}), md=2)

    return dbc.Row([
        card("📊 Vouchers Gerados", f"{total}", media(total), proj(total)),
        card("📦 Dispositivos Captados", f"{captados}", media(captados), proj(captados)),
        card("💰 Captação Total", f"R$ {valor_total:,.2f}", media(valor_total), proj(valor_total)),
        card("📍 Ticket Médio", f"R$ {ticket:,.2f}"),
        card("📈 Conversão", f"{conversao:.2f}%")
    ], justify='between')

def gerar_graficos(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    mes_vigente = df['criado em'].dt.month.max()
    df = df[df['criado em'].dt.month == mes_vigente]
    usados = usados[usados['criado em'].dt.month == mes_vigente]

    def linha(data, y_col, titulo, y_label):
        serie = data.groupby('dia')[y_col].mean() if y_col != 'Qtd' else data.groupby('dia').size()
        media = serie.mean()
        movel = serie.rolling(3, min_periods=1).mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=serie.index, y=serie.values, mode='lines+markers+text', name=titulo,
                                 text=[f"{v:.0f}" for v in serie], textposition='top center', line=dict(color='lime')))
        fig.add_trace(go.Scatter(x=movel.index, y=movel.values, name='Média Móvel', mode='lines', line=dict(color='lime', dash='dash')))
        fig.add_trace(go.Scatter(x=serie.index, y=[media]*len(serie), name='Média Simples', mode='lines', line=dict(color='blue', dash='dot')))
        fig.update_layout(template='plotly_dark', title=titulo, xaxis=dict(title='Dia', tickmode='linear'),
                          yaxis_title=y_label, plot_bgcolor='black', paper_bgcolor='black', margin=dict(t=30, b=40))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
        return fig

    return dbc.Row([
        dbc.Col(dcc.Graph(figure=linha(df, 'Qtd', "📅 Vouchers Gerados por Dia", 'Qtd')), md=4),
        dbc.Col(dcc.Graph(figure=linha(usados, 'Qtd', "📅 Vouchers Utilizados por Dia", 'Qtd')), md=4),
        dbc.Col(dcc.Graph(figure=linha(usados, 'valor do voucher', "🎫 Ticket Médio Diário", 'Média')), md=4)
    ])

def gerar_graficos_mensais(df):
    df['mes_curto'] = df['criado em'].dt.strftime('%b')
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    meses = sorted(df['mes_curto'].unique(), key=lambda x: datetime.strptime(x, "%b").month)

    def bar(df_, y, title):
        fig = px.bar(df_, x='mes_curto', y=y, text=y, title=title, category_orders={'mes_curto': meses})
        fig.update_traces(textposition='outside')
        fig.update_layout(margin=dict(t=30, b=50), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False), plot_bgcolor='white', paper_bgcolor='white')
        return fig

    return dbc.Row([
        dbc.Col(dcc.Graph(figure=bar(df.groupby('mes_curto').size().reset_index(name='Qtd'), 'Qtd', "📅 Vouchers Gerados por Mês")), md=4),
        dbc.Col(dcc.Graph(figure=bar(usados.groupby('mes_curto').size().reset_index(name='Qtd'), 'Qtd', "📅 Vouchers Utilizados por Mês")), md=4),
        dbc.Col(dcc.Graph(figure=bar(usados.groupby('mes_curto')['valor do voucher'].mean().reset_index(name='Média'), 'Média', "💳 Ticket Médio por Mês")), md=4),
    ])

def gerar_graficos_rede(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    ordem = sorted(df['mes_curto'].unique(), key=lambda x: datetime.strptime(x, "%b").month)

    def redes(data, title):
        grp = data.groupby(['nome da rede', 'mes_curto']).size().reset_index(name='Qtd')
        grp['mes_curto'] = pd.Categorical(grp['mes_curto'], categories=ordem, ordered=True)
        grp = grp.sort_values('Qtd', ascending=False)

        fig = px.bar(grp, x='nome da rede', y='Qtd', color='mes_curto', barmode='group', text='Qtd', title=title)
        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_tickangle=-45, margin=dict(t=30, b=120), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
                          plot_bgcolor='white', paper_bgcolor='white')
        return fig

    return html.Div([
        dcc.Graph(figure=redes(df, "📊 Vouchers por Rede e Mês")),
        html.Div(style={'height': '30px'}),
        dcc.Graph(figure=redes(usados, "📦 Vouchers Utilizados por Rede e Mês"))
    ])

def gerar_tabela(df):
    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    ranking = usados.groupby(['nome do vendedor', 'nome da filial', 'nome da rede']).size().reset_index(name='Qtd')
    ranking = ranking.sort_values('Qtd', ascending=False).head(10)
    return html.Div([
        html.H5("🏆 Top 10 Vendedores por Volume de Vouchers"),
        dash_table.DataTable(
            columns=[{'name': i, 'id': i} for i in ranking.columns],
            data=ranking.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            style_header={'backgroundColor': 'black', 'color': 'white'}
        )
    ])

# ========================
# 🔚 EXECUÇÃO
# ========================
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 8080)), host='0.0.0.0')
