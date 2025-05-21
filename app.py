import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
import io
import os
from datetime import datetime
import locale

# --- Inicialização da aplicação ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard de Resultados"

# --- Configurações ---
REQUIRED_COLUMNS = ['Criado em', 'Situacao do voucher', 'Valor do voucher', 'Nome da rede', 'Nome do vendedor', 'Nome da filial', 'Descrição']
COLUMN_ALIASES = {
    'Criado em': ['Criado em', 'Data de criação', 'Data criação'],
    'Situacao do voucher': ['Situacao do voucher', 'Situação do voucher'],
    'Valor do voucher': ['Valor do voucher', 'Valor Voucher', 'Valor'],
    'Nome da rede': ['Nome da rede', 'Rede'],
    'Nome do vendedor': ['Nome do vendedor', 'Vendedor'],
    'Nome da filial': ['Nome da filial', 'Filial'],
    'Descrição': ['Descrição', 'Descricao', 'Produto']
}

# --- Funções auxiliares ---
def encontrar_coluna_padrao(colunas, nome_padrao):
    for alias in COLUMN_ALIASES[nome_padrao]:
        for col in colunas:
            if col.strip().lower() == alias.strip().lower():
                return col
    return None

def processar_arquivo(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))
    df.columns = df.columns.str.strip()

    col_map = {}
    for padrao in REQUIRED_COLUMNS:
        encontrado = encontrar_coluna_padrao(df.columns, padrao)
        if encontrado:
            col_map[padrao] = encontrado
        else:
            raise ValueError(f"Coluna obrigatória ausente: {padrao}")

    df.rename(columns={v: k for k, v in col_map.items()}, inplace=True)
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df[df['Criado em'].notna()]
    df['Mês'] = df['Criado em'].dt.month_name(locale='en_US.utf8')
    return df

def kpi_card(titulo, valor, icon=""):
    return dbc.Card(
        dbc.CardBody([
            html.Div(f"{icon} {titulo}", className="card-title", style={"fontWeight": "bold"}),
            html.H4(valor, className="card-text")
        ]),
        style={"backgroundColor": "#1e1e1e", "color": "white", "border": "2px solid #00c896", "borderRadius": "10px"}
    )

# --- Layout ---
app.layout = dbc.Container(fluid=True, children=[
    html.H1("Dashboard de Resultados", style={"textAlign": "center", "marginTop": "10px", "marginBottom": "20px"}),

    dcc.Upload(
        id='upload-data',
        children=html.Div(["📁 Arraste ou selecione o arquivo .xlsx"]),
        style={
            "width": "100%", "height": "60px", "lineHeight": "60px",
            "borderWidth": "2px", "borderStyle": "dashed", "borderRadius": "10px",
            "textAlign": "center", "marginBottom": "20px", "backgroundColor": "#f9f9f9"
        },
        multiple=False
    ),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id="month-filter", placeholder="Mês"), md=4),
        dbc.Col(dcc.Dropdown(id="rede-filter", placeholder="Nome da rede"), md=4),
        dbc.Col(dcc.Dropdown(id="situacao-filter", placeholder="Situação do voucher", multi=True), md=4),
    ], className="mb-4"),

    dbc.Row(id="kpi-container", className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id='vouchers-gerados'), md=4),
        dbc.Col(dcc.Graph(id='vouchers-utilizados'), md=4),
        dbc.Col(dcc.Graph(id='ticket-medio'), md=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dash_table.DataTable(id='top-vendedores', style_table={"overflowX": "auto"}, style_cell={'fontSize': '12px'}), md=6),
        dbc.Col(dcc.Graph(id='top-dispositivos'), md=6),
    ], className="mb-4"),

    dcc.Store(id="filtered-data")
])

# --- Callback: Upload de Dados e filtros iniciais ---
@app.callback(
    Output("month-filter", "options"),
    Output("month-filter", "value"),
    Output("rede-filter", "options"),
    Output("situacao-filter", "options"),
    Output("filtered-data", "data"),
    Input("upload-data", "contents"),
)
def atualizar_filtros(contents):
    if contents is None:
        return [], None, [], [], None
    try:
        df = processar_arquivo(contents)
        latest_month = df["Mês"].dropna().unique()[0]
        return (
            [{"label": m, "value": m} for m in sorted(df["Mês"].unique())],
            latest_month,
            [{"label": rede, "value": rede} for rede in sorted(df["Nome da rede"].dropna().unique())],
            [{"label": s, "value": s} for s in sorted(df["Situacao do voucher"].dropna().unique())],
            df.to_json(date_format='iso', orient='split')
        )
    except Exception as e:
        return [], None, [], [], None

# --- Callback: Atualização do Painel ---
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
def update_dashboard(json_data, selected_month, selected_rede, selected_status):
    if json_data is None:
        return [kpi_card("Sem dados", "-", "🚫")] * 4, go.Figure(), go.Figure(), go.Figure(), [], [], go.Figure()

    df = pd.read_json(io.StringIO(json_data), orient='split')

    # Filtros
    if selected_month:
        df = df[df['Mês'] == selected_month]
    if selected_rede:
        df = df[df['Nome da rede'] == selected_rede]
    if selected_status:
        df = df[df['Situacao do voucher'].isin(selected_status)]

    df_utilizados = df[df['Situacao do voucher'].str.upper() == 'UTILIZADO']

    total_gerados = len(df)
    total_utilizados = len(df_utilizados)
    valor_total = df_utilizados["Valor do voucher"].sum()
    ticket_medio = df_utilizados["Valor do voucher"].mean() if total_utilizados else 0
    conversao = (total_utilizados / total_gerados) * 100 if total_gerados else 0

    kpis = [
        dbc.Col(kpi_card("Vouchers Gerados", total_gerados, "📄"), md=3),
        dbc.Col(kpi_card("Dispositivos Captados", total_utilizados, "📦"), md=3),
        dbc.Col(kpi_card("Captação Total", f"R$ {valor_total:,.2f}", "💰"), md=3),
        dbc.Col(kpi_card("Ticket Médio", f"R$ {ticket_medio:,.2f}", "📊"), md=3),
        # dbc.Col(kpi_card("Conversão", f"{conversao:.2f}%", "📈"), md=3),
    ]
    kpis.append(dbc.Col(kpi_card("Conversão", f"{conversao:.2f}%", "📈"), md=3))

    fig_gerados = px.line(df, x="Criado em", title="Vouchers Gerados por Dia").update_traces(mode="lines+markers")
    fig_utilizados = px.line(df_utilizados, x="Criado em", title="Vouchers Utilizados por Dia").update_traces(mode="lines+markers")
    fig_ticket = px.line(
        df_utilizados.groupby("Criado em")["Valor do voucher"].mean().reset_index(),
        x="Criado em",
        y="Valor do voucher",
        title="Ticket Médio Diário"
    ).update_traces(mode="lines+markers")

    # Top vendedores
    ranking_df = df_utilizados.groupby(["Nome do vendedor", "Nome da filial"]).size().reset_index(name="Quantidade")
    ranking_df = ranking_df.sort_values(by="Quantidade", ascending=False).reset_index(drop=True)
    ranking_df.insert(0, "Ranking", ranking_df.index + 1)

    top_vendedores_data = ranking_df.to_dict("records")
    top_vendedores_columns = [{"name": col, "id": col} for col in ranking_df.columns]

    # Top dispositivos
    top_dispositivos = df["Descrição"].value_counts().nlargest(10).reset_index()
    top_dispositivos.columns = ["Descrição", "Quantidade"]
    fig_dispositivos = px.bar(top_dispositivos, x="Descrição", y="Quantidade", title="Top Dispositivos")

    return kpis, fig_gerados, fig_utilizados, fig_ticket, top_vendedores_data, top_vendedores_columns, fig_dispositivos

# --- Execução ---
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
