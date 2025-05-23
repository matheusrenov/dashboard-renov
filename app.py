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
    html.Div(id='graficos-mensais', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='ranking-vendedores', style={'marginTop': '20px'})
])
@app.callback(
    Output('filtros', 'children'),
    Output('kpi-cards', 'children'),
    Output('graficos-mensais', 'children'),
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

        colunas_esperadas = ['imei', 'criado em', 'valor do voucher', 'valor do dispositivo', 'situacao do voucher', 'nome do vendedor', 'nome da filial', 'nome da rede']
        for col in colunas_esperadas:
            if col not in df.columns:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
        df['mes_curto'] = df['criado em'].dt.strftime('%b')  # Ex: Jan, Feb, Mar
        df['mes_curto'] = pd.Categorical(df['mes_curto'], categories=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], ordered=True)
        df['mes'] = df['criado em'].dt.strftime('%b')
        df['dia'] = df['criado em'].dt.day.astype(str)
        df['mes_ordem'] = df['criado em'].dt.month

        app.df_original = df

        filtros_layout = dbc.Row([
            dbc.Col(dcc.Dropdown(id='filtro-mes', options=[{'label': m, 'value': m} for m in sorted(df['mes'].unique(), key=lambda x: datetime.strptime(x, "%b").month)], multi=True, placeholder="Mês"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-rede', options=[{'label': r, 'value': r} for r in sorted(df['nome da rede'].dropna().unique())], multi=True, placeholder="Rede"), md=4),
            dbc.Col(dcc.Dropdown(id='filtro-situacao', options=[{'label': s, 'value': s} for s in sorted(df['situacao do voucher'].dropna().unique())], multi=True, placeholder="Situação do voucher"), md=4),
        ], style={'marginTop': '20px'})

        return filtros_layout, gerar_kpis(df), gerar_graficos_mensais(df), gerar_graficos(df), gerar_tabela(df), ""

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"Erro ao processar: {str(e)}"
@app.callback(
    Output('kpi-cards', 'children', allow_duplicate=True),
    Output('graficos-mensais', 'children', allow_duplicate=True),
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

    return gerar_kpis(df), gerar_graficos_mensais(df), gerar_graficos(df), gerar_tabela(df)

def gerar_kpis(df):
    total_gerados = len(df)
    utilizados = df[df['situacao do voucher'].str.lower() == 'utilizado']
    dispositivos = len(utilizados)
    captacao = utilizados['valor do dispositivo'].sum()
    ticket = captacao / dispositivos if dispositivos > 0 else 0
    conversao = dispositivos / total_gerados * 100 if total_gerados > 0 else 0

    return dbc.Row([
        dbc.Col(dbc.Card([
            html.H5("📊 Vouchers Gerados"),
            html.H3(f"{total_gerados}")
        ], body=True, color="dark", inverse=True, style={"border": "2px solid lime"}), md=2),

        dbc.Col(dbc.Card([
            html.H5("📦 Dispositivos Captados"),
            html.H3(f"{dispositivos}")
        ], body=True, color="dark", inverse=True, style={"border": "2px solid lime"}), md=2),

        dbc.Col(dbc.Card([
            html.H5("💰 Captação Total"),
            html.H3(f"R$ {captacao:,.2f}")
        ], body=True, color="dark", inverse=True, style={"border": "2px solid lime"}), md=2),

        dbc.Col(dbc.Card([
            html.H5("📍 Ticket Médio"),
            html.H3(f"R$ {ticket:,.2f}")
        ], body=True, color="dark", inverse=True, style={"border": "2px solid lime"}), md=2),

        dbc.Col(dbc.Card([
            html.H5("📈 Conversão"),
            html.H3(f"{conversao:.2f}%")
        ], body=True, color="dark", inverse=True, style={"border": "2px solid lime"}), md=2),
    ], justify='between', style={'marginBottom': 30})
def gerar_graficos_mensais(df):
    df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')
    df['mes_curto'] = df['criado em'].dt.strftime('%b')  # Ex: Jan, Feb...
    df['mes_num'] = df['criado em'].dt.month
    df = df.sort_values('mes_num')  # garante a ordem correta

    usados = df[df['situacao do voucher'].str.lower() == 'utilizado']

    # Vouchers Gerados por Mês
    fig_gerados = px.bar(
        df.groupby(['mes_curto', 'mes_num']).size().reset_index(name='Qtd').sort_values('mes_num'),
        x='mes_curto', y='Qtd', text='Qtd', title="📅 Vouchers Gerados por Mês"
    )

    # Vouchers Utilizados por Mês
    fig_utilizados = px.bar(
        usados.groupby(['mes_curto', 'mes_num']).size().reset_index(name='Qtd').sort_values('mes_num'),
        x='mes_curto', y='Qtd', text='Qtd', title="📅 Vouchers Utilizados por Mês"
    )

    # Ticket Médio por Mês
    fig_ticket = px.bar(
        usados.groupby(['mes_curto', 'mes_num'])['valor do voucher'].mean().reset_index(name='Média').sort_values('mes_num'),
        x='mes_curto', y='Média', text='Média', title="💳 Ticket Médio por Mês"
    )

    # Aplicar estilo a todos os gráficos
    for fig in [fig_gerados, fig_utilizados, fig_ticket]:
        fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False),
            margin=dict(l=20, r=20, t=50, b=30),
        )

    return dbc.Row([
        dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
        dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
        dbc.Col(dcc.Graph(figure=fig_ticket), md=4),
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
        fig.add_trace(go.Scatter(x=series.index, y=series.values, mode='lines+markers+text', name=title,
                                 text=[f"{v:.0f}" for v in series.values],
                                 textposition='top center',
                                 line=dict(color='lime')))
        fig.add_trace(go.Scatter(x=serie_media_movel.index, y=serie_media_movel.values, mode='lines',
                                 name='Média Móvel', line=dict(color='lime', dash='dash')))
        fig.add_trace(go.Scatter(x=series.index, y=[media_simples]*len(series), mode='lines',
                                 name='Média', line=dict(color='blue', dash='dot')))
        fig.update_layout(template='plotly_dark', title=title,
                          plot_bgcolor='black', paper_bgcolor='black',
                          xaxis=dict(title='dia', tickmode='linear'),
                          yaxis_title=y_label)
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
# 🔥 Execução
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
