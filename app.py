import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import base64
import io
import os
import dash_bootstrap_components as dbc

# Layout de login removido por simplicidade

# App
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Dashboard com Debug"

REQUIRED_COLUMNS = [
    'Criado em', 'Situacao do voucher', 'Valor do voucher',
    'Nome da rede', 'Nome do vendedor', 'Nome da filial', 'Descrição'
]

COLUMN_ALIASES = {
    'Criado em': ['Criado em', 'Data de criação', 'Data criação'],
    'Situacao do voucher': ['Situacao do voucher', 'Situação do voucher'],
    'Valor do voucher': ['Valor do voucher', 'Valor Voucher', 'Valor'],
    'Nome da rede': ['Nome da rede', 'Rede'],
    'Nome do vendedor': ['Nome do vendedor', 'Vendedor'],
    'Nome da filial': ['Nome da filial', 'Filial'],
    'Descrição': ['Descrição', 'Descricao', 'Produto']
}

def encontrar_coluna_padrao(colunas, nome_padrao):
    for alias in COLUMN_ALIASES[nome_padrao]:
        for col in colunas:
            if col.strip().lower() == alias.strip().lower():
                return col
    return None

def process_data(contents):
    print("[DEBUG] Iniciando processamento de upload...")

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded))
    df.columns = df.columns.str.strip()

    print("[DEBUG] Colunas encontradas:", df.columns.tolist())

    col_map = {}
    for padrao in REQUIRED_COLUMNS:
        encontrado = encontrar_coluna_padrao(df.columns, padrao)
        if encontrado:
            col_map[padrao] = encontrado
        else:
            raise ValueError(f"❌ Coluna obrigatória ausente: {padrao}")

    df.rename(columns={v: k for k, v in col_map.items()}, inplace=True)

    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    df = df[df['Criado em'].notna()]
    df['Mês'] = df['Criado em'].dt.month

    print("[DEBUG] Upload processado com sucesso. Linhas:", len(df))
    return df

# Layout
app.layout = dbc.Container([
    html.H3("Upload com Debug de Planilha"),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Clique ou arraste um arquivo Excel aqui.']),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed',
            'borderRadius': '10px', 'textAlign': 'center',
            'backgroundColor': '#f0f0f0'
        },
        multiple=False
    ),
    html.Div(id='output-debug'),
    dash_table.DataTable(id='preview-table', style_table={'overflowX': 'auto'})
], fluid=True)

@app.callback(
    [Output('output-debug', 'children'),
     Output('preview-table', 'data'),
     Output('preview-table', 'columns')],
    Input('upload-data', 'contents')
)
def carregar_dados(contents):
    if contents is None:
        return "", [], []

    try:
        df = process_data(contents)
        msg = f"✅ Upload realizado com sucesso! Linhas carregadas: {len(df)}"
        return msg, df.to_dict('records'), [{"name": i, "id": i} for i in df.columns]
    except Exception as e:
        print("[ERRO NO UPLOAD]", str(e))
        return f"❌ Erro ao processar arquivo: {str(e)}", [], []

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
