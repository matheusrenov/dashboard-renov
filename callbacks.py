from datetime import datetime
import dash
from dash import Input, Output, State
import pandas as pd
from models import ImportHistory
from app import app

@app.callback(
    [Output("last-import-info", "children"),
     Output("output-data-upload", "children")],
    [Input("update-networks", "n_clicks"),
     Input("update-employees", "n_clicks"),
     Input('upload-data', 'contents')],
    [State('upload-data', 'filename'),
     State('current-user', 'data')]
)
def handle_imports(network_clicks, employee_clicks, contents, filename, current_user):
    ctx = dash.callback_context
    if not ctx.triggered:
        # Recuperar última importação
        import_history = ImportHistory()
        last_imports = import_history.get_last_imports(2)
        import_info = []
        for imp in last_imports:
            import_info.append(f"{imp['import_type']}: {imp['import_date'].strftime('%d/%m/%Y %H:%M')}")
        return ", ".join(import_info), ""

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        import_history = ImportHistory()
        
        if button_id == "update-networks":
            # Lógica para processar o arquivo de redes
            df = pd.DataFrame()  # Será substituído pela lógica real de leitura do arquivo
            
            import_history.add_import(
                import_type='redes_filiais',
                filename='planilha_redes.xlsx',
                imported_by=current_user['id'] if current_user else None,
                row_count=len(df)
            )
            
        elif button_id == "update-employees":
            # Lógica para processar o arquivo de colaboradores
            df = pd.DataFrame()  # Será substituído pela lógica real de leitura do arquivo
            
            import_history.add_import(
                import_type='colaboradores',
                filename='planilha_colaboradores.xlsx',
                imported_by=current_user['id'] if current_user else None,
                row_count=len(df)
            )
            
        elif button_id == "upload-data" and contents:
            # Lógica para processar o arquivo de dados
            pass
            
        # Recuperar informações atualizadas
        last_imports = import_history.get_last_imports(2)
        import_info = []
        for imp in last_imports:
            import_info.append(f"{imp['import_type']}: {imp['import_date'].strftime('%d/%m/%Y %H:%M')}")
        
        return ", ".join(import_info), "Importação realizada com sucesso!"
        
    except Exception as e:
        return "Erro na importação", f"Erro: {str(e)}" 