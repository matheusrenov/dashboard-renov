import dash_bootstrap_components as dbc
from dash import html, dcc

def create_upload_section():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            dcc.Upload(
                                id='upload-data',
                                children=dbc.Button(
                                    "Upload Performance",
                                    color="primary",
                                    size="sm",
                                    className="me-2"
                                ),
                                multiple=False
                            ),
                            dbc.Button(
                                "Atualizar Base de Redes e Filiais",
                                id="update-networks",
                                color="secondary",
                                size="sm",
                                className="me-2"
                            ),
                            dbc.Button(
                                "Atualizar Base de Colaboradores",
                                id="update-employees",
                                color="secondary",
                                size="sm"
                            ),
                        ], width=12, className="d-flex justify-content-start align-items-center")
                    ]),
                    html.Div(id='output-data-upload'),
                    
                    # Informações da última importação
                    html.Div([
                        html.Small([
                            html.Span("Última atualização: ", className="fw-bold"),
                            html.Span(id="last-import-info", className="text-muted")
                        ], className="mt-2")
                    ])
                ], className="mb-4")
            ])
        ])
    ]) 