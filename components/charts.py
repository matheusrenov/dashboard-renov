import plotly.express as px

def grafico_captacao_diaria(df):
    df_util = df[df["Situacao do voucher"] == "UTILIZADO"]
    agrupado = df_util.groupby("Criado em")["Valor do voucher"].sum().reset_index()

    fig = px.line(
        agrupado,
        x="Criado em",
        y="Valor do voucher",
        title="Captação diária em R$ (Dispositivos Usados)",
        markers=True,
        template="plotly_dark",
        color_discrete_sequence=["#00C896"]
    )
    return fig
