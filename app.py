import os
import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
from unidecode import unidecode
from datetime import datetime

# Inicializa o app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Layout principal
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
    
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'})
])

# Callback do upload
@app.callback(
    Output('kpi-cards', 'children'),
    Output('graficos', 'children'),
    Output('error-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def processar_arquivo(contents, filename):
    if contents is None:
        return dash.no_update, dash.no_update, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))

        # Blindagem: normaliza e loga colunas
        df.columns = [unidecode(col).strip().lower() for col in df.columns]
        print("Colunas disponíveis:", df.columns.tolist())

        # Colunas obrigatórias
        colunas_esperadas = ['imei', 'criado em', 'valor do voucher', 'situacao do voucher']
        for col in colunas_esperadas:
            if col not in df.columns:
                return dash.no_update, dash.no_update, f"❌ Coluna obrigatória não encontrada: {col}"

        # Conversões
        df['criado em'] = pd.to_datetime(df['criado em'], errors='coerce')

        # KPIs
        total_gerados = df.shape[0]
        dispositivos = df['imei'].nunique()
        captacao = df['valor do voucher'].sum()
        ticket = captacao / dispositivos if dispositivos > 0 else 0
        usados = df[df['situacao do voucher'].str.lower() == 'utilizado']
        conversao = len(usados) / total_gerados * 100 if total_gerados > 0 else 0

        kpis = dbc.Row([
            dbc.Col(dbc.Card([
                html.H5("📊 Vouchers Gerados"),
                html.H3(f"{total_gerados}")
            ], body=True, color="dark", inverse=True), md=3),

            dbc.Col(dbc.Card([
                html.H5("📦 Dispositivos Captados"),
                html.H3(f"{dispositivos}")
            ], body=True, color="dark", inverse=True), md=3),

            dbc.Col(dbc.Card([
                html.H5("💰 Captação Total"),
                html.H3(f"R$ {captacao:,.2f}")
            ], body=True, color="dark", inverse=True), md=3),

            dbc.Col(dbc.Card([
                html.H5("🎯 Ticket Médio"),
                html.H3(f"R$ {ticket:,.2f}")
            ], body=True, color="dark", inverse=True), md=3),

            dbc.Col(dbc.Card([
                html.H5("📈 Conversão"),
                html.H3(f"{conversao:.2f}%")
            ], body=True, color="dark", inverse=True), md=3),
        ])

        # Gráficos
        df['data'] = df['criado em'].dt.date
        usados['data'] = usados['criado em'].dt.date

        fig_gerados = px.line(
            df.groupby('data').size().reset_index(name='Qtd'),
            x='data', y='Qtd', title="📆 Vouchers Gerados por Dia"
        )

        fig_utilizados = px.line(
            usados.groupby('data').size().reset_index(name='Qtd'),
            x='data', y='Qtd', title="📆 Vouchers Utilizados por Dia"
        )

        fig_ticket = px.line(
            usados.groupby('data')['valor do voucher'].mean().reset_index(name='Média'),
            x='data', y='Média', title="🎫 Ticket Médio Diário"
        )

        graficos = dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_gerados), md=4),
            dbc.Col(dcc.Graph(figure=fig_utilizados), md=4),
            dbc.Col(dcc.Graph(figure=fig_ticket), md=4),
        ])

        return kpis, graficos, ""

    except Exception as e:
        return dash.no_update, dash.no_update, f"Erro ao processar arquivo: {str(e)}"

# Inicialização correta com Dash 3+
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
