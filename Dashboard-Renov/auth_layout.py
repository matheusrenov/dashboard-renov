import dash_bootstrap_components as dbc
from dash import html

def create_login_layout():
    """
    Cria o layout da página de login.
    
    Returns:
        Componente HTML com o layout de login
    """
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Img(
                        src='./assets/images/Logo Roxo.png',
                        style={"height": "50px", "marginBottom": "20px"}
                    ),
                    html.H2("Login", className="text-center mb-4"),
                    dbc.Input(
                        id="login-username",
                        type="text",
                        placeholder="Usuário",
                        className="mb-3"
                    ),
                    dbc.Input(
                        id="login-password",
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
                    html.Div([
                        html.A("Esqueceu sua senha?", href="#", className="text-muted"),
                        html.Span(" | ", className="text-muted"),
                        html.A("Registrar", href="#", className="text-muted")
                    ], className="text-center")
                ], className="p-4 bg-white rounded shadow-sm")
            ], md=6, lg=4, className="mx-auto")
        ], className="vh-100 align-items-center")
    ], fluid=True, className="bg-light")

def create_register_layout():
    """
    Cria o layout da página de registro.
    
    Returns:
        Componente HTML com o layout de registro
    """
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Img(
                        src='./assets/images/Logo Roxo.png',
                        style={"height": "50px", "marginBottom": "20px"}
                    ),
                    html.H2("Registro", className="text-center mb-4"),
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
                        color="primary",
                        className="w-100 mb-3"
                    ),
                    html.Div([
                        html.Span("Já tem uma conta? ", className="text-muted"),
                        html.A("Faça login", href="#", className="text-primary")
                    ], className="text-center")
                ], className="p-4 bg-white rounded shadow-sm")
            ], md=6, lg=4, className="mx-auto")
        ], className="vh-100 align-items-center")
    ], fluid=True, className="bg-light")

def create_admin_approval_layout():
    """
    Cria o layout da página de aprovação de administrador.
    
    Returns:
        Componente HTML com o layout de aprovação
    """
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Img(
                        src='./assets/images/Logo Roxo.png',
                        style={"height": "50px", "marginBottom": "20px"}
                    ),
                    html.H2("Aprovação Pendente", className="text-center mb-4"),
                    html.P(
                        "Sua conta está aguardando aprovação do administrador. "
                        "Você será notificado por email quando sua conta for aprovada.",
                        className="text-muted text-center mb-4"
                    ),
                    dbc.Button(
                        "Voltar para Login",
                        href="/login",
                        color="primary",
                        className="w-100"
                    )
                ], className="p-4 bg-white rounded shadow-sm")
            ], md=6, lg=4, className="mx-auto")
        ], className="vh-100 align-items-center")
    ], fluid=True, className="bg-light") 