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

# Inicialização do app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
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

    html.Div([
        dbc.Row([
            dbc.Col(dcc.Dropdown(id='month-filter', placeholder="Mês"), md=4),
            dbc.Col(dcc.Dropdown(id='rede-filter', placeholder="Nome da rede"), md=4),
            dbc.Col(dcc.Dropdown(id='situacao-filter', placeholder="Situação do voucher"), md=4)
        ])
    ], style={'marginTop': 20, 'marginBottom': 20}),

    dcc.Store(id='filtered-data'),
    html.Div(id='kpi-cards', style={'marginTop': '20px'}),
    html.Div(id='graficos', style={'marginTop': '20px'}),
    html.Div(id='tabela-ranking', style={'marginTop': '20px'})
])
