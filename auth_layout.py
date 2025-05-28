import dash_bootstrap_components as dbc
from dash import html, dcc

def create_login_layout():
    return html.Div(className="auth-container", children=[
        dbc.Card(className="auth-card", style={"width": "400px"}, children=[
            dbc.CardBody([
                html.Div(className="auth-header text-center", children=[
                    html.Img(src="assets/logo-renov.png", style={"maxWidth": "200px"}),
                    html.H3("Login", className="mb-4")
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Usuário"),
                        dbc.Input(id="login-username", type="text", placeholder="Digite seu usuário")
                    ], className="mb-3"),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Senha"),
                        dbc.Input(id="login-password", type="password", placeholder="Digite sua senha")
                    ], className="mb-4"),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Entrar", id="login-button", color="primary", className="w-100 mb-3", n_clicks=0)
                    ])
                ]),
                dbc.Row([
                    dbc.Col([
                        html.A("Criar nova conta", id="show-register", href="#", className="auth-link")
                    ], className="text-center")
                ])
            ])
        ])
    ])

def create_register_layout():
    return html.Div(className="auth-container", children=[
        dbc.Card(className="auth-card", style={"width": "400px"}, children=[
            dbc.CardBody([
                html.Div(className="auth-header text-center", children=[
                    html.Img(src="assets/logo-renov.png", style={"maxWidth": "200px"}),
                    html.H3("Registro", className="mb-4")
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Usuário"),
                        dbc.Input(id="register-username", type="text", placeholder="Escolha um usuário")
                    ], className="mb-3"),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Email"),
                        dbc.Input(id="register-email", type="email", placeholder="Digite seu email")
                    ], className="mb-3"),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Senha"),
                        dbc.Input(id="register-password", type="password", placeholder="Escolha uma senha")
                    ], className="mb-3"),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Confirmar Senha"),
                        dbc.Input(id="register-confirm-password", type="password", placeholder="Confirme sua senha")
                    ], className="mb-4"),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Registrar", id="register-button", color="success", className="w-100 mb-3", n_clicks=0)
                    ])
                ]),
                dbc.Row([
                    dbc.Col([
                        html.A("Voltar para login", id="show-login", href="#", className="auth-link")
                    ], className="text-center")
                ])
            ])
        ])
    ])

def create_admin_approval_layout():
    return html.Div([
        html.H4("👥 Aprovação de Usuários", className="mb-4"),
        html.Div(id="pending-users-table"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Aprovar", id="approve-user-button", color="success", className="me-2"),
                dbc.Button("Rejeitar", id="reject-user-button", color="danger")
            ], width=12, className="mt-3")
        ])
    ]) 