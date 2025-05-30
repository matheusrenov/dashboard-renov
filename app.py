import os
import base64
import io
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from unidecode import unidecode
import warnings
from models import UserDatabase
from models_network import NetworkDatabase
from auth_layout import create_login_layout, create_register_layout, create_admin_approval_layout
from error_layout import create_error_layout
from dash.exceptions import PreventUpdate
from dotenv import load_dotenv
import secrets
from flask_cors import CORS
from flask import Flask, jsonify
import socket
import psutil
from typing import cast, Union, Any, Dict
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from custom_types import PsutilValue, PercentageValue, SystemStatus

load_dotenv()  # carrega variáveis do .env se existir

# Inicializa o SQLAlchemy
db = SQLAlchemy()

# ========================
# 🔧 Funções Utilitárias
# ========================

def check_port(port: int) -> bool:
    """Verifica se uma porta está disponível"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return True
        except OSError:
            return False

def get_available_port(start_port: int = 8080) -> int:
    """Encontra uma porta disponível"""
    port = start_port
    while not check_port(port):
        port += 1
        if port > start_port + 100:  # Limite de tentativas
            raise RuntimeError("Não foi possível encontrar uma porta disponível")
    return port

def check_system_health() -> Dict[str, Any]:
    """Verifica a saúde do sistema"""
    try:
        # Verifica uso de CPU
        cpu_percent: float = cast(float, psutil.cpu_percent(interval=1))
        
        # Verifica uso de memória
        memory = psutil.virtual_memory()
        memory_percent: float = cast(float, memory.percent)
        
        # Verifica espaço em disco
        disk = psutil.disk_usage('/')
        disk_percent: float = cast(float, disk.percent)
        
        # Verifica conexão com o banco de dados
        db_status = True
        try:
            user_db = UserDatabase()
            db_status = user_db.test_connection()
        except Exception:
            db_status = False

        # Define o status inicial
        status = 'healthy'
        cpu_status = 'ok'
        memory_status = 'ok'
        disk_status = 'ok'

        # Verifica CPU
        if cpu_percent > 90:
            status = 'unhealthy'
            cpu_status = 'critical'
        elif cpu_percent > 70:
            cpu_status = 'warning'

        # Verifica Memória
        if memory_percent > 90:
            status = 'unhealthy'
            memory_status = 'critical'
        elif memory_percent > 70:
            memory_status = 'warning'

        # Verifica Disco
        if disk_percent > 90:
            status = 'unhealthy'
            disk_status = 'critical'
        elif disk_percent > 70:
            disk_status = 'warning'

        # Se o banco de dados estiver com erro, sistema está unhealthy
        if not db_status:
            status = 'unhealthy'

        return {
            'status': status,
            'cpu': {'value': cpu_percent, 'status': cpu_status},
            'memory': {'value': memory_percent, 'status': memory_status},
            'disk': {'value': disk_percent, 'status': disk_status},
            'database': {'status': 'ok' if db_status else 'error'}
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# ========================
# 🚀 Inicialização do App
# ========================

# Configuração dos assets
assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
if not os.path.exists(assets_path):
    os.makedirs(assets_path)

# Configuração da porta
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'  # Sempre usa 0.0.0.0 para aceitar conexões externas

# Inicialização do Flask
server = Flask(__name__)

# Inicialização do Dash com todas as configurações necessárias
app = dash.Dash(
    __name__,
    server=cast(Any, server),
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    update_title='Carregando...',
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ],
    assets_folder=assets_path,
    serve_locally=True,
    routes_pathname_prefix='/'
) 