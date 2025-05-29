import dash_bootstrap_components as dbc
from dash import html, dcc

def create_login_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Img(
                                    src="assets/logo-renov.png",
                                    style={
                                        "maxWidth": "180px",
                                        "width": "100%",
                                        "height": "auto",
                                        "marginBottom": "1rem"
                                    },
                                    className="logo-image"
                                )
                            ], className="logo-container"),
                        ], className="text-center"),
                        
                        dbc.Input(
                            id="login-username",
                            type="text",
                            placeholder="Usuário",
                            className="mb-3 auth-input"
                        ),
                        
                        dbc.Input(
                            id="login-password",
                            type="password",
                            placeholder="Senha",
                            className="mb-4 auth-input"
                        ),
                        
                        dbc.Button(
                            "Entrar",
                            id="login-button",
                            color="primary",
                            className="w-100 mb-3 auth-button",
                            n_clicks=0
                        ),
                        
                        html.Div([
                            dbc.Button(
                                "Criar nova conta",
                                id="show-register",
                                color="link",
                                className="p-0 auth-link"
                            )
                        ], className="text-center")
                    ])
                ], className="auth-card")
            ], width=12, md=6, lg=4, className="mx-auto")
        ], className="min-vh-100 align-items-center")
    ], fluid=True, className="auth-container")

def create_register_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Img(
                                    src="assets/logo-renov.png",
                                    style={
                                        "maxWidth": "180px",
                                        "width": "100%",
                                        "height": "auto",
                                        "marginBottom": "1rem"
                                    },
                                    className="logo-image"
                                )
                            ], className="logo-container"),
                        ], className="text-center"),
                        
                        dbc.Input(
                            id="register-username",
                            type="text",
                            placeholder="Usuário",
                            className="mb-3 auth-input"
                        ),
                        
                        dbc.Input(
                            id="register-email",
                            type="email",
                            placeholder="Email",
                            className="mb-3 auth-input"
                        ),
                        
                        dbc.Input(
                            id="register-password",
                            type="password",
                            placeholder="Senha",
                            className="mb-3 auth-input"
                        ),
                        
                        dbc.Input(
                            id="register-confirm-password",
                            type="password",
                            placeholder="Confirmar Senha",
                            className="mb-4 auth-input"
                        ),
                        
                        dbc.Button(
                            "Registrar",
                            id="register-button",
                            color="success",
                            className="w-100 mb-3 auth-button",
                            n_clicks=0
                        ),
                        
                        html.Div([
                            dbc.Button(
                                "Voltar para login",
                                id="show-login",
                                color="link",
                                className="p-0 auth-link"
                            )
                        ], className="text-center")
                    ])
                ], className="auth-card")
            ], width=12, md=6, lg=4, className="mx-auto")
        ], className="min-vh-100 align-items-center")
    ], fluid=True, className="auth-container")

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