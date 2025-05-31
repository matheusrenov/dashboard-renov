# -*- coding: utf-8 -*-
"""
Dashboard Renov - Aplicação principal

Este módulo contém a aplicação principal do Dashboard Renov, responsável por:
- Visualização e análise de dados de vouchers
- Gestão de redes e colaboradores
- Monitoramento de performance
- Geração de relatórios e KPIs
"""

# Bibliotecas padrão
import os
import io
import base64
import secrets
import traceback
import socket
from datetime import datetime, timedelta
from typing import Dict, Any, Union, cast, TypeVar

# Bibliotecas de dados e análise
import pandas as pd
import numpy as np
from unidecode import unidecode

# Monitoramento do sistema
import psutil

# Flask e extensões
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Dash e componentes
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, dash_table, callback_context, no_update
from dash.exceptions import PreventUpdate

# Plotly para gráficos
import plotly.graph_objects as go
import plotly.express as px

# Exportação de dados
import xlsxwriter

# Módulos locais
from models import UserDatabase
from models_network import NetworkDatabase
from auth_layout import create_login_layout, create_register_layout, create_admin_approval_layout
from error_layout import create_error_layout

# Tipos personalizados
PsutilValue = TypeVar('PsutilValue', float, int)
PercentageValue = float
SystemStatus = Dict[str, Union[
    str,
    Dict[str, Union[PsutilValue, str]],
    Dict[str, str],
    str
]]

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()  # carrega variáveis do .env se existir

# Configuração dos assets
assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
if not os.path.exists(assets_path):
    os.makedirs(assets_path)

# Configuração da porta
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'

# Inicialização do Flask
server = Flask(__name__)

# Configurações do Flask
server.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(16)),
    FLASK_ENV='production',
    DEBUG=False,
    PORT=PORT,
    HOST=HOST,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    PREFERRED_URL_SCHEME='https',
    PROXY_FIX_X_FOR=1,
    PROXY_FIX_X_PROTO=1,
    PROXY_FIX_X_HOST=1,
    PROXY_FIX_X_PORT=1,
    PROXY_FIX_X_PREFIX=1
)

# Configuração do SQLAlchemy
server.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/dashboard.db'
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurações de segurança
CORS(server, resources={r"/*": {"origins": "*"}})

# Inicialização do Dash
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    update_title='Carregando...',
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ],
    assets_folder=assets_path,
    serve_locally=True
)

# Configurações do Dash
app.title = "Dashboard Renov"
app.config.suppress_callback_exceptions = True

# Inicializa o SQLAlchemy
db = SQLAlchemy(server)

# ========================
# 🔧 Funções Utilitárias
# ========================

// ... existing code ...