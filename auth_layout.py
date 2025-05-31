"""
Layouts de autenticação
"""
import dash_bootstrap_components as dbc
from dash import html, dcc

def create_login_layout():
    """Cria o layout de login"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H2("Login", className="text-center mb-4"),
                        dbc.Input(
                            id="username",
                            placeholder="Usuário",
                            type="text",
                            className="mb-3"
                        ),
                        dbc.Input(
                            id="password",
                            placeholder="Senha",
                            type="password",
                            className="mb-3"
                        ),
                        dbc.Button(
                            "Entrar",
                            id="login-button",
                            color="primary",
                            className="w-100"
                            )
                    ])
                ], className="shadow")
            ], width=6)
        ], justify="center", className="mt-5")
    ])

def create_register_layout():
    """Cria o layout de registro"""
    return html.Div("Registro não implementado")

def create_admin_approval_layout():
    """Cria o layout de aprovação admin"""
    return html.Div("Aprovação admin não implementada") 