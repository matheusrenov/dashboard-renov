import dash_bootstrap_components as dbc
from dash import html, dcc

def create_login_layout(error_message=None):
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Img(
                        src='assets/images/Logo Roxo.png',
                        style={"height": "50px", "marginBottom": "20px"}
                    ),
                    html.H2("Login", className="text-center mb-4"),
                    dbc.Input(
                        id="username",
                        type="text",
                        placeholder="Usuário",
                        className="mb-3"
                    ),
                    dbc.Input(
                        id="password",
                        type="password",
                        placeholder="Senha",
                        className="mb-3"
                    ),
                    dbc.Button(
                        "Entrar",
                        id="login-button",
                        color="primary",
                        className="w-100 mb-3"
                    ),
                    html.Div(id="auth-status")
                ], className="p-4 bg-white rounded shadow-sm")
            ], md=6, lg=4, className="mx-auto")
        ], className="vh-100 align-items-center")
    ], fluid=True, className="bg-light")

def create_register_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Img(
                                src='./assets/images/Logo Roxo.png',
                                style={
                                    "width": "150px",
                                    "marginBottom": "20px",
                                    "display": "inline-block"
                                }
                            )
                        ], className="text-center mb-4"),
                        
                        dbc.Input(
                            id="register-username",
                            type="text",
                            placeholder="Usuário",
                            className="mb-3"
                        ),
                        
                        dbc.Input(
                            id="register-email",
                            type="email",
                            placeholder="Email",
                            className="mb-3"
                        ),
                        
                        dbc.Input(
                            id="register-password",
                            type="password",
                            placeholder="Senha",
                            className="mb-3"
                        ),
                        
                        dbc.Input(
                            id="register-confirm-password",
                            type="password",
                            placeholder="Confirmar Senha",
                            className="mb-3"
                        ),
                        
                        dbc.Button(
                            "Registrar",
                            id="register-button",
                            color="success",
                            className="w-100 mb-3",
                            n_clicks=0
                        ),
                        
                        html.Div([
                            dbc.Button(
                                "Voltar para login",
                                id="show-login",
                                color="link",
                                className="p-0"
                            )
                        ], className="text-center")
                    ])
                ], className="shadow", style={"maxWidth": "400px", "width": "100%"})
            ], width=12, className="d-flex justify-content-center")
        ], className="min-vh-100 align-items-center")
    ], fluid=True, className="bg-light")

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