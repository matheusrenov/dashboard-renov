import os
import base64
import io
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html, dash_table
import plotly.express as px
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Layout principal
app.layout = html.Div([
    html.H2("Dashboard de Resultados", style={"textAlign": "center", "marginTop": 20}),
    dcc.Upload(
        id="upload-data",
        children=html.Div(["📁 Arraste ou selecione o arquivo .xlsx"]),
        style={
            "width": "100%", "height": "60px", "lineHeight": "60px",
            "borderWidth": "2px", "borderStyle": "dashed",
            "borderRadius": "5px", "textAlign": "center", "margin": "10px 0"
        },
        multiple=False
    ),
    html.Div(id="upload-error", style={"color": "red", "textAlign": "center"}),

    html.Div([
        dcc.Dropdown(id='month-filter', placeholder="Mês", style={'marginRight': '10px'}),
        dcc.Dropdown(id='rede-filter', placeholder="Nome da rede", style={'marginRight': '10px'}),
        dcc.Dropdown(id='situacao-filter', placeholder="Situação do voucher"),
    ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '10px'}),

    dcc.Store(id='filtered-data'),
    
    html.Div(id='kpi-container', style={'display': 'flex', 'gap': '10px'}),

    html.Div([
        dcc.Graph(id='vouchers-gerados'),
        dcc.Graph(id='vouchers-utilizados'),
        dcc.Graph(id='ticket-medio')
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '10px'}),

    html.Div([
        html.Div([
            dash_table.DataTable(id='top-vendedores',
                                 style_table={'overflowX': 'auto'},
                                 style_cell={'fontSize': 12, 'textAlign': 'left'},
                                 page_size=15)
        ], style={'width': '60%'}),
        dcc.Graph(id='top-dispositivos', style={'width': '38%'})
    ], style={'display': 'flex', 'gap': '2%', 'marginTop': '20px'}),
])

# Callback para processar upload
@app.callback(
    Output("filtered-data", "data"),
    Output("month-filter", "options"),
    Output("rede-filter", "options"),
    Output("situacao-filter", "options"),
    Output("upload-error", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename")
)
def processar_arquivo(conteudo, nome_arquivo):
    if conteudo is None:
        return dash.no_update, [], [], [], ""

    try:
        content_type, content_string = conteudo.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        
        df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
        df.dropna(subset=['Criado em'], inplace=True)
        df['Mês'] = df['Criado em'].dt.month_name().str.capitalize()

        meses = sorted(df['Mês'].dropna().unique().tolist())
        redes = sorted(df['Nome da rede'].dropna().unique().tolist())
        situacoes = sorted(df['Situação do voucher'].dropna().unique().tolist())

        options_meses = [{"label": m, "value": m} for m in meses]
        options_redes = [{"label": r, "value": r} for r in redes]
        options_situacao = [{"label": s, "value": s} for s in situacoes]

        return df.to_dict('records'), options_meses, options_redes, options_situacao, ""
    except Exception as e:
        return None, [], [], [], f"Erro ao processar arquivo: {e}"


# Callback principal
@app.callback(
    Output("kpi-container", "children"),
    Output("vouchers-gerados", "figure"),
    Output("vouchers-utilizados", "figure"),
    Output("ticket-medio", "figure"),
    Output("top-vendedores", "data"),
    Output("top-vendedores", "columns"),
    Output("top-dispositivos", "figure"),
    Input("filtered-data", "data"),
    Input("month-filter", "value"),
    Input("rede-filter", "value"),
    Input("situacao-filter", "value")
)
def atualizar_dashboard(data, mes, rede, situacao):
    if data is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    df = pd.DataFrame(data)

    # Filtros
    if mes:
        df = df[df['Mês'] == mes]
    if rede:
        df = df[df['Nome da rede'] == rede]
    if situacao:
        df = df[df['Situação do voucher'] == situacao]

    # KPIs
    total_dispositivos = len(df)
    total_cap = df['Valor do voucher'].sum()
    ticket_medio = df['Valor do voucher'].mean() if not df.empty else 0
    utilizados = df[df['Situação do voucher'] == 'UTILIZADO']
    taxa_conversao = (len(utilizados) / total_dispositivos) * 100 if total_dispositivos else 0

    kpis = [
        dbc.Card([
            html.H6("📊 Vouchers Gerados", style={"color": "white"}),
            html.H4(f"{total_dispositivos}", style={"color": "white"})
        ], color="dark", body=True, style={"border": "2px solid cyan"}),

        dbc.Card([
            html.H6("💰 Captação Total", style={"color": "white"}),
            html.H4(f"R$ {total_cap:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), style={"color": "white"})
        ], color="dark", body=True, style={"border": "2px solid cyan"}),

        dbc.Card([
            html.H6("📊 Ticket Médio", style={"color": "white"}),
            html.H4(f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), style={"color": "white"})
        ], color="dark", body=True, style={"border": "2px solid cyan"}),

        dbc.Card([
            html.H6("📉 Conversão", style={"color": "white"}),
            html.H4(f"{taxa_conversao:.2f}%", style={"color": "white"})
        ], color="dark", body=True, style={"border": "2px solid cyan"})
    ]

    # Gráficos
    fig_gerados = px.line(df, x='Criado em', y=df.groupby(df['Criado em'].dt.date)['ID'].count().values,
                          labels={'x': 'Data', 'y': 'Vouchers'}, title="Vouchers Gerados por Dia")
    fig_utilizados = px.line(utilizados, x='Criado em', y=utilizados.groupby(utilizados['Criado em'].dt.date)['ID'].count().values,
                             labels={'x': 'Data', 'y': 'Utilizados'}, title="Vouchers Utilizados por Dia")
    fig_ticket = px.line(df, x='Criado em', y='Valor do voucher', title="Ticket Médio Diário")

    for fig in [fig_gerados, fig_utilizados, fig_ticket]:
        fig.update_layout(xaxis_tickformat="%d/%b", template="plotly_white", height=350)

    # Tabela vendedores
    top_vend = df[df['Situação do voucher'] == 'UTILIZADO'].groupby(
        ['Nome do vendedor', 'Nome da filial', 'Nome da rede'])['ID'].count().reset_index(name='Quantidade')
    top_vend.sort_values(by='Quantidade', ascending=False, inplace=True)
    top_vend.insert(0, 'Ranking', range(1, len(top_vend)+1))

    columns = [{"name": i, "id": i} for i in top_vend.columns]

    # Top dispositivos
    top_disp = df['Descrição'].value_counts().reset_index()
    top_disp.columns = ['Descrição', 'Quantidade']
    fig_disp = px.bar(top_disp.head(10), x='Descrição', y='Quantidade', title="Top Dispositivos")
    fig_disp.update_layout(xaxis_tickangle=-45, height=400)

    return kpis, fig_gerados, fig_utilizados, fig_ticket, top_vend.to_dict("records"), columns, fig_disp

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
