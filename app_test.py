import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import os

# Inicialização do app
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
server = app.server

# Layout principal
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
    html.Div(id='auth-status')
])

# Layout de login
def create_login_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("📊 Dashboard Renov", className="text-center mb-4"),
                dbc.Card([
                    dbc.CardBody([
                        html.H3("Login", className="text-center mb-4"),
                        dbc.Input(
                            id="login-username",
                            placeholder="Email",
                            type="email",
                            className="mb-3"
                        ),
                        dbc.Input(
                            id="login-password",
                            placeholder="Senha",
                            type="password",
                            className="mb-3"
                        ),
                        dbc.Button(
                            "Entrar",
                            id="login-button",
                            color="primary",
                            className="w-100 mb-3"
                        ),
                        html.Hr(),
                        html.P("Não tem uma conta?", className="text-center"),
                        dbc.Button(
                            "Registrar",
                            id="show-register",
                            color="secondary",
                            className="w-100"
                        )
                    ])
                ], className="shadow-sm")
            ], md=6, lg=4, className="mx-auto")
        ], className="align-items-center min-vh-100")
    ], fluid=True, className="bg-light")

# Layout do dashboard
def create_dashboard_layout():
    return html.Div([
        html.H1("Dashboard", className="text-center"),
        dbc.Button("Sair", id="logout-button", color="danger")
    ])

# Callback de roteamento
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    print(f"Roteamento para: {pathname}")
    if pathname == '/dashboard':
        return create_dashboard_layout()
    return create_login_layout()

# Callback de login
@app.callback(
    [Output('url', 'pathname', allow_duplicate=True),
     Output('auth-status', 'children')],
    [Input('login-button', 'n_clicks')],
    [State('login-username', 'value'),
     State('login-password', 'value')],
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password):
    if not n_clicks:
        raise PreventUpdate
    
    if username == "admin@renov.com.br" and password == "admin":
        return '/dashboard', dbc.Alert("Login realizado com sucesso!", color="success", duration=2000)
    
    return no_update, dbc.Alert("Usuário ou senha inválidos.", color="danger", duration=4000)

# Callback de logout
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    [Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    if n_clicks:
        return '/'
    raise PreventUpdate

if __name__ == '__main__':
    print("Iniciando servidor...")
    app.run_server(
        debug=True,
        host='localhost',
        port=8081
    ) 