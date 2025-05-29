from datetime import datetime
import dash
from dash import Input, Output, State
import pandas as pd
from models import ImportHistory
from app import app
from typing import Optional, Dict, Any, Union

def get_safe_user_id(user_data: Optional[Dict[str, Any]]) -> int:
    """
    Extrai o ID do usuário de forma segura, retornando um valor padrão se não encontrado
    
    Args:
        user_data: Dicionário com dados do usuário ou None
        
    Returns:
        int: ID do usuário ou 1 (sistema) se não encontrado
    """
    try:
        if user_data and isinstance(user_data, dict) and 'id' in user_data:
            user_id = int(user_data['id'])
            if user_id > 0:
                return user_id
    except (ValueError, TypeError):
        pass
    return 1  # ID padrão para sistema

@app.callback(
    [Output("last-import-info", "children"),
     Output("output-data-upload", "children")],
    [Input("update-networks", "n_clicks"),
     Input("update-employees", "n_clicks"),
     Input('upload-data', 'contents')],
    [State('upload-data', 'filename'),
     State('current-user', 'data')]
)
def handle_imports(
    network_clicks: Optional[int], 
    employee_clicks: Optional[int], 
    contents: Optional[str], 
    filename: Optional[str], 
    current_user: Optional[Dict[str, Any]]
) -> tuple[str, str]:
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
        user_id = get_safe_user_id(current_user)
        
        if button_id == "update-networks":
            # Lógica para processar o arquivo de redes
            df = pd.DataFrame()  # Será substituído pela lógica real de leitura do arquivo
            
            import_history.add_import(
                import_type='redes_filiais',
                filename='planilha_redes.xlsx',
                imported_by=user_id,
                row_count=len(df)
            )
            
        elif button_id == "update-employees":
            # Lógica para processar o arquivo de colaboradores
            df = pd.DataFrame()  # Será substituído pela lógica real de leitura do arquivo
            
            import_history.add_import(
                import_type='colaboradores',
                filename='planilha_colaboradores.xlsx',
                imported_by=user_id,
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