from dash import html

def kpi_card(title, value, delta, icon="📊", color="#00FFAA"):
    return html.Div([
        html.H4(f"{icon} {title}", style={"color": color, "margin": "0"}),
        html.H2(value, style={"color": "white", "margin": "5px 0"}),
        html.P(f"Variação: {delta}", style={"color": "gray", "margin": "0"})
    ], style={
        "backgroundColor": "#1E1E1E",
        "padding": "20px",
        "borderRadius": "10px",
        "marginBottom": "10px",
        "borderLeft": "5px solid " + str(color)
    })
