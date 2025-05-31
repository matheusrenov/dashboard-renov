"""
Layouts de erro
"""
import dash_bootstrap_components as dbc
from dash import html

def create_error_layout(error_code='404'):
    """Cria o layout de erro"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1(f"Erro {error_code}", className="text-center"),
                html.P("Página não encontrada", className="text-center"),
                dbc.Button("Voltar ao início", href="/", color="primary")
            ], width=6)
        ], justify="center", className="mt-5")
    ]) 