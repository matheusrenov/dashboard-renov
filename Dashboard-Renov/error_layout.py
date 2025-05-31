import dash_bootstrap_components as dbc
from dash import html

def create_error_layout(error_code: str = '404'):
    """
    Cria o layout da página de erro.
    
    Args:
        error_code: Código do erro (404, 500, etc)
    
    Returns:
        Componente HTML com o layout de erro
    """
    error_messages = {
        '404': {
            'title': 'Página não encontrada',
            'message': 'A página que você está procurando não existe.'
        },
        '500': {
            'title': 'Erro interno',
            'message': 'Ocorreu um erro interno no servidor. Tente novamente mais tarde.'
        },
        '403': {
            'title': 'Acesso negado',
            'message': 'Você não tem permissão para acessar esta página.'
        }
    }
    
    error_info = error_messages.get(error_code, {
        'title': 'Erro',
        'message': 'Ocorreu um erro inesperado.'
    })
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Img(
                        src='./assets/images/Logo Roxo.png',
                        style={"height": "50px", "marginBottom": "20px"}
                    ),
                    html.H1(
                        error_code,
                        className="display-1 text-danger text-center mb-4"
                    ),
                    html.H3(
                        error_info['title'],
                        className="text-center mb-4"
                    ),
                    html.P(
                        error_info['message'],
                        className="text-muted text-center mb-4"
                    ),
                    dbc.Button(
                        "Voltar para o Dashboard",
                        href="/dashboard",
                        color="primary",
                        className="me-2"
                    ),
                    dbc.Button(
                        "Ir para Login",
                        href="/login",
                        color="secondary"
                    )
                ], className="text-center")
            ], md=6, className="mx-auto")
        ], className="vh-100 align-items-center")
    ], fluid=True, className="bg-light") 