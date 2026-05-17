import os
import httpx
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

API = os.getenv("API_BASE_URL", "http://fastapi:8000")

st.set_page_config(
    page_title="Valorisation des actions du CAC 40",
    page_icon="💰",
    layout="wide"
)

@st.cache_data(ttl=60)
def create_df(period: str = "5Y", tickers: tuple[str, ...] = ("ENGI.PA",)) -> pd.DataFrame:
    r = httpx.get(f"{API}", params={"period": period, "ticker": list(tickers)}, timeout=30.0)
    if r.status_code != 200:
        return pd.DataFrame()
    df = pd.DataFrame(r.json()["data"])
    return df


@st.cache_data(ttl=300)
def get_tickers_options() -> list:
    """Récupère la liste des tickers disponibles."""
    return httpx.get(f"{API}/tickers").json()["tickers"]
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def line_chart(data_filtered: pd.DataFrame) -> None:
    if data_filtered.empty:
        st.info("Aucune donnée disponible pour la sélection.")
        return

    data = data_filtered.reset_index(drop=True)
    y_min = data_filtered["Close"].min()
    y_max = data_filtered["Close"].max()

    nearest = alt.selection_point(
        name="Select",
        encodings=["x", "y"],
        on="mouseover",
        empty=False,
        nearest=True,
    )

    tooltip = [
        alt.Tooltip("Ticker:N", title="Entreprise"),
        alt.Tooltip("Date:O", title="Date"),
        alt.Tooltip("Close:Q", title="Cours de clôture", format=".2f"),
    ]

    line = (
        alt.Chart(data)
        .mark_line(point=False)
        .encode(
            x=alt.X(
                "Date:O",
                title="Day",
                # axis=alt.Axis(format="%m/%Y", labelAngle=90, tickCount="month"),
            ),
            y=alt.Y(
                "Close:Q",
                title="Cours de clôture",
                scale=alt.Scale(domain=[y_min, y_max]),
            ),
            color=alt.Color("Ticker:N", title="Entreprise"),
        )
    )

    selectors = (
        alt.Chart(data)
        .mark_point(opacity=0, size=200)
        .encode(
            x="Date:O",
            y="Close:Q",
            color="Ticker:N",
            tooltip=tooltip,
        )
        .add_params(nearest)
    )

    rules = (
        alt.Chart(data)
        .mark_rule(color="gray")
        .encode(x="Date:O")
        .transform_filter(nearest)
    )

    # Point + tooltip sur la courbe la plus proche de la souris (x et y)
    points = (
        alt.Chart(data)
        .mark_point(color="red", size=70)
        .encode(
            x="Date:O",
            y="Close:Q",
            color="Ticker:N",
            tooltip=tooltip,
        )
        .transform_filter(nearest)
    )

    # Combine
    line_chart = alt.layer(line, selectors, rules, points)

    st.altair_chart(line_chart, width="stretch")

with st.sidebar:
    st.header("val.cac40")

    st.session_state["ticker_selected"]  = st.pills("ENTREPRISES", get_tickers_options(), selection_mode="multi", default=get_tickers_options()[0])
    
    st.session_state["period_filter"] = st.pills("PÉRIODE", ["1M", "6M", "CY", "1Y", "5Y"], selection_mode="single", required=True, default="5Y")

    ratio = st.pills("RATIO", ["P/E Ratio", "P/S Ratio", "Dividend Yield"], selection_mode="single", required=True, default="P/E Ratio")


# Show Title
st.title("Valorisation des actions du CAC 40", text_alignment="left")

période = {"1M": "1 mois", "6M": "6 mois", "CY": "Cette année", "1Y": "1 an", "5Y": "5 ans"}

st.write(f"{len(st.session_state['ticker_selected'])} entreprise(s) sélectionnée(s)  ·  {ratio}  ·  {période[st.session_state['period_filter']]} ")

selected_tickers = st.session_state.get("ticker_selected") or []
if isinstance(selected_tickers, str):
    selected_tickers = [selected_tickers]
data = create_df(st.session_state["period_filter"], tuple(selected_tickers))

# Fetch metrics from API
if st.session_state["ticker_selected"]:
    with st.container(horizontal=True):
        for entreprise in st.session_state["ticker_selected"]:
            metrics_response = httpx.get(
                f"{API}/metrics",
                params={"period": st.session_state["period_filter"], "ticker": entreprise}
            )

            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
                current_price = metrics["current_price"]
                percentage_change = metrics["percentage_change"]

                st.metric(f"{entreprise} cours", f"{current_price:.2f}€", f"{percentage_change:+.2f}%", border=True)

# Show line chart
line_chart(data)

# Show description
col1, col2, col3 = st.columns(3)
with col1:
    with st.popover("*cours de clôture*", icon="❓"):
        st.write("""
    **Définition**  
    Le cours de clôture est le prix de l'action à la fin de la journée de négociation.

    ---

    **Importance pour les investisseurs**  
    C'est une référence importante car elle reflète la valeur réelle de l'action à un moment donné.

    **Utilisations principales**
    - Calculer les rendements
    - Analyser les indicateurs techniques
    - Prendre des décisions d'investissement

    **Facteurs d'influence**
    - Nouvelles économiques
    - Résultats financiers de l'entreprise
    - Événements mondiaux
    - Tendances du marché
    """)
with col2:
    with st.popover("*Volume*", icon="❓"):
        st.write("""
        **Définition**  
        Le volume est le nombre total d'actions échangées lors d'une journée de négociation.

        ---

        **Importance pour les investisseurs**  
        Un volume élevé indique un fort intérêt pour l'actif, ce qui peut renforcer la confiance des investisseurs.

        **Utilisations principales**
        - Analyser la liquidité du marché
        - Identifier les tendances de prix
        - Valider les signaux techniques

        **Facteurs d'influence**
        - Nouvelles économiques
        - Résultats financiers de l'entreprise
        - Événements mondiaux
        - Tendances du marché
        """)        
col1, col2, col3 = st.columns(3)
with col1:
    st.popover("P/E Ratio", icon="❓").write("""
    **Définition**  
    Le ratio P/E (Price-to-Earnings) est un indicateur de valorisation qui compare le prix de l'action aux bénéfices par action (EPS) de l'entreprise.  

    **Calcul**  
    P/E Ratio = Prix de l'action / Bénéfice par action (EPS)
    """)
with col2:
    st.popover("PEG Ratio", icon="❓").write("""
    **Définition**  
    Le ratio PEG (Price-to-Earnings Growth) est un indicateur de valorisation qui tient compte de la croissance des bénéfices.

    **Calcul**  
    PEG Ratio = P/E Ratio / Croissance des bénéfices
    """)
with col3:
    st.popover("Dividend Yield", icon="❓").write("""
    **Définition**  
    Le rendement des dividendes est le rapport entre les dividendes versés par une action et son prix de marché.

    **Calcul**  
    Dividend Yield = (Dividende par action / Prix de l'action) * 100
    """)

# -------------------------------------
#  Footer
# -------------------------------------
        
st.markdown(
    """
<hr style="margin-top:50px;">
<div style="margin-top:30px;">
pour en savoir plus sur la bourse: <a href=https://www.economie.gouv.fr/facileco/dossiers-economiques/la-bourse> economie.gouv.fr </a> 
</div>
<div style="text-align: left; font-size: 0.9em; margin-top:30px">
© 2026 MAREY--GUIDI Nathan — Stock Analysis Introduction <br>
built with Streamlit, Airflow & Fast API<br>
<i>For educational purposes only — not financial advice</i>
</div>
""",
    unsafe_allow_html=True,
)
