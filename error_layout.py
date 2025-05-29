import dash_bootstrap_components as dbc
from dash import html

def create_error_layout(error_type="deploy", error_message=None, error_details=None):
    """
    Cria um layout de erro personalizado baseado no tipo de erro
    
    Args:
        error_type (str): Tipo do erro ('deploy', 'healthcheck', 'network', etc)
        error_message (str): Mensagem principal do erro
        error_details (str): Detalhes adicionais do erro
    """
    
    error_configs = {
        'deploy': {
            'icon': '🚨',
            'title': 'Erro no Deploy',
            'color': 'danger',
            'default_message': 'Ocorreu um erro durante o deploy da aplicação.'
        },
        'healthcheck': {
            'icon': '🏥',
            'title': 'Falha no Healthcheck',
            'color': 'warning',
            'default_message': 'O healthcheck da aplicação falhou.'
        },
        'network': {
            'icon': '🌐',
            'title': 'Erro de Rede',
            'color': 'danger',
            'default_message': 'Ocorreu um erro de rede durante o processo.'
        }
    }
    
    config = error_configs.get(error_type, error_configs['deploy'])
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.H1([
                                config['icon'],
                                " ",
                                config['title']
                            ], className="text-center mb-4"),
                            
                            html.Div([
                                html.H4(error_message or config['default_message'], 
                                      className=f"text-{config['color']} text-center mb-4"),
                                
                                html.Div([
                                    html.P("Detalhes técnicos:", className="fw-bold mb-2"),
                                    html.Pre(error_details, 
                                           className="bg-light p-3 rounded",
                                           style={"whiteSpace": "pre-wrap"})
                                ] if error_details else []),
                                
                                html.Hr(),
                                
                                html.Div([
                                    html.P("Sugestões de resolução:", className="fw-bold mb-2"),
                                    html.Ul([
                                        html.Li("Verifique se todos os serviços necessários estão rodando"),
                                        html.Li("Confirme se as variáveis de ambiente estão configuradas corretamente"),
                                        html.Li("Verifique os logs do servidor para mais detalhes"),
                                        html.Li("Tente reiniciar a aplicação"),
                                        html.Li([
                                            "Se o problema persistir, entre em contato com o suporte: ",
                                            html.A("suporte@renov.com.br", 
                                                  href="mailto:suporte@renov.com.br",
                                                  className="text-primary")
                                        ])
                                    ], className="mb-4")
                                ]),
                                
                                html.Div([
                                    dbc.Button(
                                        "Tentar Novamente",
                                        id="retry-button",
                                        color="primary",
                                        className="me-2"
                                    ),
                                    dbc.Button(
                                        "Voltar para Home",
                                        id="return-home-button",
                                        color="secondary"
                                    )
                                ], className="text-center")
                            ], className="text-center")
                        ])
                    ])
                ], className="shadow-lg")
            ], md=8, lg=6, className="mx-auto")
        ], className="min-vh-100 align-items-center")
    ], fluid=True, className="bg-light py-5") 