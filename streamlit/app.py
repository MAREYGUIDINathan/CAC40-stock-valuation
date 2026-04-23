import os
import httpx
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

API = os.getenv("API_BASE_URL", "http://fastapi:8000")


@st.cache_data(ttl=60)
def create_df(period: str = "5y", ticker: str = "ENGI.PA") -> pd.DataFrame:
    r = httpx.get(f"{API}", params={"period": period, "ticker": ticker})
    if r.status_code == 200:
        return pd.DataFrame(r.json()["data"]).set_index("Date")
    return pd.DataFrame()


@st.cache_data(ttl=300)
def get_tickers_options() -> list:
    """Récupère la liste des tickers disponibles."""
    return httpx.get(f"{API}/tickers").json()["tickers"]


def init_session_state():
    """Initialise les variables du session_state."""
    defaults = {
        "ticker_selected": "ENGI.PA",
        "period_filter": "5y"
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def create_sync_ticker_selectbox(label: str, key: str):
    """Crée un selectbox synchronized automatiquement avec tous les autres ticker_selectbox.
    
    Tous les selectbox avec une clé commençant par 'ticker_select_' seront synchronisés automatiquement.
    Aucune configuration supplémentaire n'est nécessaire.
    """
    options = get_tickers_options()
    
    # Initialise la clé si elle n'existe pas
    if key not in st.session_state:
        st.session_state[key] = "ENGI.PA"
    
    def sync_callback():
        selected_value = st.session_state[key]
        st.session_state["ticker_selected"] = selected_value
        # Sync tous les autres selectbox ticker automatiquement
        for session_key in st.session_state.keys():
            if session_key.startswith("ticker_select_") and session_key != key:
                st.session_state[session_key] = selected_value
    
    st.selectbox(
        label,
        options=options,
        key=key,
        on_change=sync_callback
    )


def line_chart(data_filtered: pd.DataFrame) -> None:
    # Affichage d'un graphique centré sur la moyenne avec une échelle pertinente (Close vs. Datetime)
    data = data_filtered.reset_index()
    y_min = data_filtered["Close"].min()
    y_max = data_filtered["Close"].max()

    # Utilise selection_point pour la sélection "hover"
    nearest = alt.selection_point(
        name="Select",
        encodings=["x"],
        on="mouseover",
        empty=False,
        nearest=True,
    )

    # Line chart
    line = (
        alt.Chart(data)
        .mark_line()
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
            tooltip=[
                alt.Tooltip("Date:O", title="Date"),
                alt.Tooltip("Close:Q", title="Cours de clôture"),
            ],
        )
    )

    # Sélecteurs transparents pour la détection du hover
    selectors = (
        alt.Chart(data)
        .mark_point(color="transparent")
        .encode(
            x="Date:O",
            y="Close:Q",
        )
        .add_params(nearest)
    )

    # Droite verticale qui suit la souris (sélection)
    rules = (
        alt.Chart(data)
        .mark_rule(color="gray")
        .encode(
            x="Date:O",
        )
        .transform_filter(nearest)
    )

    # Afficher un point sur la courbe sous la souris
    points = (
        alt.Chart(data)
        .mark_point(color="red", size=70)
        .encode(x="Date:O", y="Close:Q")
        .transform_filter(nearest)
    )

    # Combine
    line_chart = alt.layer(line, selectors, rules, points)

    st.altair_chart(line_chart, width="stretch")


# Show Title
st.title("Introduction to Stock Market", text_alignment="center")

# -------------------------------------
#   Sommaire
# -------------------------------------

# -------------------------------------
#   Introduction
# -------------------------------------

st.subheader("Introduction")
st.write("""
Bienvenue dans cette application d'introduction à la bourse !  

Ici, vous pouvez explorer les données de marché de différentes actions, comprendre les concepts clés de la bourse, et apprendre comment les investisseurs prennent des décisions basées sur les données.  

Que vous soyez un débutant ou que vous souhaitez approfondir vos connaissances, cette application est conçue pour vous !   
""")

# -------------------------------------
#   Les Fondamentaux de la Bourse
# -------------------------------------

st.subheader("I - Les Fondamentaux de la Bourse")

st.write("""
La bourse est un marché où s’échangent des produits financiers, appelés « instruments financiers », ou valeurs mobilières.  
 
Les différents instruments financiers sont :  

- les **actions** (titres de propriété d'une partie du capital d'une entreprise), 
- les **obligations** (prêt d'argent contractuel à un organisme public ou privé), 
- les **parts d'OPCVM** (Organismes de Placement Collectif en Valeurs Mobilières).  

Devenir propriétaire d'une valeurs mobilières donne accèes à des droits: 
""")
col1, col2, col3 = st.columns(3)
with col1:
    with st.container(border=True):
        st.write("""
        ##### Action
        - Dividende
        - Vote aux assemblées des actionnaires
        """)
with col2:
    with st.container(border=True):
        st.write("""
        ##### Obligation
        - Intérêt versé chaque années
        - Remboursement à la fin du contrat
        """)
with col3:
    with st.container(border=True):
        st.write("""
        ##### OPCVM
        - Propre à chaque OPCVM
        """)
        
st.write("""
Comme sur tous les marchés, le prix dépend de l’offre et de la demande. Si l’offre est supérieure à la demande, le prix diminue pour atteindre l’équilibre.  
À l’inverse, quand la demande est supérieure à l’offre, le prix augmente pour atteindre l’équilibre.  

La fonction première de la Bourse est de permettre aux investisseurs d’acheter et de vendre leurs titres sur le marché secondaire. C’est ce qu’on appelle la liquidité(marché sur lequel ont lieu beaucoup de transactions.)
""")

# -------------------------------------
# II - Comprendre ce qu'on achète
# -------------------------------------

st.subheader("II - Comprendre ce qu'on achète")
col1, col2 = st.columns(2, border=True)
with col1:
    st.markdown("""##### Action""")
    st.write("""
    Une action représente une part de propriété dans une entreprise.  

    En achetant une action, vous devenez actionnaire de cette entreprise et vous avez droit à une partie de ses bénéfices, ainsi qu'à une voix lors des assemblées générales.  

    Il est important de faire des recherches sur l'entreprise avant d'investir.  
    Cela inclut la compréhension de son modèle économique, de sa position sur le marché, de sa santé financière, et de ses perspectives de croissance.  
    """)
with col2:
    st.markdown("""##### Valeur vs. Prix""")
    st.write("""
    Le prix d'une action est simplement le montant que les investisseurs sont prêts à payer pour une part de l'entreprise à un moment donné.  
    
    La valeur de l'entreprise, en revanche, est une estimation de ce que l'entreprise vaut réellement, basée sur ses actifs, ses revenus, sa croissance potentielle, et d'autres facteurs fondamentaux.  
    
    Il est possible qu'une action soit surévaluée (prix élevé par rapport à la valeur) ou sous-évaluée (prix bas par rapport à la valeur).
    """)


# -------------------------------------
#  III - Les Données Essentielles
# -------------------------------------

# Show subtitle
st.subheader(
    "III - Les Données Essentielles",
)

init_session_state()

create_sync_ticker_selectbox("Sélectionnez une action", "ticker_select_1")

st.write(f"Cours de cloture de : **{st.session_state['ticker_selected']}**")

if "period_filter" not in st.session_state:
    st.session_state["period_filter"] = "5y"

# Show button
with st.container(horizontal=True, horizontal_alignment="left"):
    if st.button("1M", type="secondary"):
        st.session_state["period_filter"] = "1m"
    if st.button("6M"):
        st.session_state["period_filter"] = "6m"
    if st.button("CY"):
        st.session_state["period_filter"] = "CY"
    if st.button("1Y"):
        st.session_state["period_filter"] = "1y"
    if st.button("5Y"):
        st.session_state["period_filter"] = "5y"

data = create_df(st.session_state["period_filter"], st.session_state["ticker_selected"])

# Fetch metrics from API
metrics_response = httpx.get(
    f"{API}/metrics",
    params={"period": st.session_state["period_filter"], "ticker": st.session_state["ticker_selected"]}
)

if metrics_response.status_code == 200:
    metrics = metrics_response.json()
    current_price = metrics["current_price"]
    percentage_change = metrics["percentage_change"]
    average_volume = metrics["average_volume"]

    # Display metrics in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Cours actuel", f"€{current_price:.2f}", f"{percentage_change:+.2f}%")
    with col2:
        st.metric("Variation sur la période", f"{percentage_change:+.2f}%", 
                  delta_color="green" if percentage_change >= 0 else "red")
    with col3:
        st.metric("Volume moyen par jour", f"{metrics['average_volume']:.0f}")
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
        
# -------------------------------------
# IV - Valorisation de l'Entreprise
# -------------------------------------

st.subheader("IV - Valorisation de l'Entreprise")

create_sync_ticker_selectbox("Sélectionnez une action", "ticker_select_2")

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
#  V - Santé Financière
# -------------------------------------
st.subheader("V - Santé Financière")
create_sync_ticker_selectbox("Sélectionnez une action", "ticker_select_3")
# -------------------------------------
#  VI - Analyse Stratégique
# -------------------------------------
st.subheader("VI - Analyse Stratégique")
create_sync_ticker_selectbox("Sélectionnez une action", "ticker_select_4")
# -------------------------------------
#  Bonus - Explorer les données
# -------------------------------------

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
