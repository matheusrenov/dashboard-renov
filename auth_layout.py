import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table

def create_login_layout():
    return html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Img(src="/assets/logo-renov.png", style={'width': '150px', 'marginBottom': '30px'}),
                        dbc.Card([
                            dbc.CardBody([
                                html.H3("Login", className="text-center mb-4"),
                                dbc.Form([
                                    dbc.Input(
                                        type="text",
                                        id="login-username",
                                        placeholder="Usuário",
                                        className="mb-3"
                                    ),
                                    dbc.Input(
                                        type="password",
                                        id="login-password",
                                        placeholder="Senha",
                                        className="mb-3"
                                    ),
                                    dbc.Button(
                                        "Entrar",
                                        id="login-button",
                                        color="primary",
                                        className="w-100 mb-3",
                                        n_clicks=0
                                    ),
                                    html.Div([
                                        html.A("Criar nova conta", href="#", id="show-register", className="text-primary")
                                    ], className="text-center")
                                ])
                            ])
                        ], className="shadow-sm auth-card")
                    ], style={
                        'maxWidth': '400px',
                        'margin': '100px auto',
                        'textAlign': 'center'
                    })
                ])
            ])
        ], fluid=True, className="auth-container")
    ])

def create_register_layout():
    return html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Img(src="/assets/logo-renov.png", style={'width': '150px', 'marginBottom': '30px'}),
                        dbc.Card([
                            dbc.CardBody([
                                html.H3("Criar Conta", className="text-center mb-4"),
                                dbc.Form([
                                    dbc.Input(
                                        type="text",
                                        id="register-username",
                                        placeholder="Usuário",
                                        className="mb-3"
                                    ),
                                    dbc.Input(
                                        type="email",
                                        id="register-email",
                                        placeholder="Email",
                                        className="mb-3"
                                    ),
                                    dbc.Input(
                                        type="password",
                                        id="register-password",
                                        placeholder="Senha",
                                        className="mb-3"
                                    ),
                                    dbc.Input(
                                        type="password",
                                        id="register-confirm-password",
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
                                        html.A("Voltar para login", href="#", id="show-login", className="text-primary")
                                    ], className="text-center")
                                ])
                            ])
                        ], className="shadow-sm auth-card")
                    ], style={
                        'maxWidth': '400px',
                        'margin': '100px auto',
                        'textAlign': 'center'
                    })
                ])
            ])
        ], fluid=True, className="auth-container")
    ])

def create_admin_approval_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H3("Aprovação de Usuários", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="pending-users-table", className="pending-users-table"),
                        dbc.Button(
                            "Voltar ao Dashboard",
                            id="back-to-dashboard",
                            color="primary",
                            className="mt-3",
                            n_clicks=0
                        )
                    ])
                ], className="shadow-sm")
            ])
        ])
    ], className="mt-4") 