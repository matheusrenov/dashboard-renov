# -*- coding: utf-8 -*-
"""
Dashboard Renov - Aplicação principal
"""

import os
import secrets
from datetime import datetime

# Flask
from flask import Flask, jsonify

# Dash
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

# Configuração básica
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(BASE_DIR, 'data')
os.makedirs(data_path, exist_ok=True)

# Flask server
server = Flask(__name__)
server.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(16)),
    DEBUG=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
)

# Dash app
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.title = "Dashboard Renov"

# Layout principal
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Callback único e simples
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    """Renderiza a página"""
    return dbc.Row([
        dbc.Col([
            html.H1("🎯 Dashboard Renov", className="text-center mb-4 text-primary"),
            dbc.Card([
                dbc.CardHeader([
                    html.H4("Sistema de Login", className="mb-0 text-center")
                ]),
                dbc.CardBody([
                    dbc.Form([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Usuário:", html_for="username"),
                                dbc.Input(
                                    id="username",
                                    placeholder="Digite seu usuário",
                                    type="text",
                                    className="mb-3"
                                )
                            ])
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Senha:", html_for="password"),
                                dbc.Input(
                                    id="password",
                                    placeholder="Digite sua senha",
                                    type="password",
                                    className="mb-3"
                                )
                            ])
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    "Entrar no Sistema",
                                    id="login-btn",
                                    color="primary",
                                    size="lg",
                                    className="w-100 mb-3"
                                )
                            ])
                        ])
                    ])
                ])
            ], className="shadow"),
            html.Hr(),
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                "Sistema funcionando no Railway! Use: admin/admin"
            ], color="info")
        ], width=6)
    ], justify="center", className="mt-5")

# Healthcheck
@server.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'app': 'dashboard-renov'
    })

# Página de teste
@server.route('/test')
def test_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard Renov - Teste</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; }
            .success { color: green; font-size: 24px; }
        </style>
    </head>
    <body>
        <h1 class="success">✅ Dashboard Renov Funcionando!</h1>
        <p>Deploy realizado com sucesso no Railway</p>
        <p>Timestamp: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
        <a href="/">Voltar ao Dashboard</a>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080) 