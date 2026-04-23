import os
import httpx
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

API = os.getenv("API_BASE_URL", "http://fastapi:8000")


@st.cache_data(ttl=60)
def create_df(period: str = "5y") -> pd.DataFrame:
    r = httpx.get(f"{API}", params={"period": period})
    if r.status_code == 200:
        return pd.DataFrame(r.json()["data"]).set_index("Date")
    return pd.DataFrame()


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
                "Date:T",
                title="Day",
                axis=alt.Axis(format="%m/%Y", labelAngle=90, tickCount="month"),
            ),
            y=alt.Y(
                "Close:Q",
                title="Cours de clôture",
                scale=alt.Scale(domain=[y_min, y_max]),
            ),
            tooltip=[
                alt.Tooltip("Date:T", title="Date"),
                alt.Tooltip("Close:Q", title="Cours de clôture"),
            ],
        )
    )

    # Sélecteurs transparents pour la détection du hover
    selectors = (
        alt.Chart(data)
        .mark_point(color="transparent")
        .encode(
            x="Date:T",
            y="Close:Q",
        )
        .add_params(nearest)
    )

    # Droite verticale qui suit la souris (sélection)
    rules = (
        alt.Chart(data)
        .mark_rule(color="gray")
        .encode(
            x="Date:T",
        )
        .transform_filter(nearest)
    )

    # Afficher un point sur la courbe sous la souris
    points = (
        alt.Chart(data)
        .mark_point(color="red", size=70)
        .encode(x="Date:T", y="Close:Q")
        .transform_filter(nearest)
    )

    # Combine
    line_chart = alt.layer(line, selectors, rules, points)

    st.altair_chart(line_chart, width="stretch")


# Show Title
st.title("Introduction to Stock Market", text_alignment="center")

st.subheader(
    "Explorer les données",
)
if "ticker_selected" not in st.session_state:
    st.session_state["ticker_selected"] = "ENGI.PA"

st.selectbox(
    "Sélectionnez une action",
    options=httpx.get(f"{API}/tickers").json()["tickers"],
    index=httpx.get(f"{API}/tickers").json()["tickers"].index(st.session_state["ticker_selected"])
)

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

data = create_df(st.session_state["period_filter"])

# Show line chart
line_chart(data)


pages = [
    [0, "La bourse"],
    [1, "Une action"],
    [2, "Une entreprise"],
    [3, "Un indice"],
    [4, "Une valorisation"],
    [5, "Un dividende"],
    [6, "Les risques et la diversification"],
]

if "page_selected" not in st.session_state:
    st.session_state["page_selected"] = 0

st.subheader("C'est quoi ?")
with st.container(horizontal=True, width="content"):
    for page in pages:
        if st.button(page[1]):
            st.session_state["page_selected"] = page[0]

match st.session_state["page_selected"]:
    case 0:
        with st.container(border=True):
            st.write("#### La bourse c'est un marché")
            st.write("""
            La Bourse est un lieu où s’échangent des produits financiers, appelés « instruments financiers », ou valeurs mobilières.  
            """)
        with st.container(border=True):
            st.write("#### Instruments financiers")
            st.write("""
            Les différents instruments financiers sont :  
            - les **actions** (titres de propriété d'une partie du capital d'une entreprise), 
            - les **obligations** (prêt d'argent contractuel à un organisme public ou privé), 
            - les **parts d'OPCVM** (Organismes de Placement Collectif en Valeurs Mobilières).
            """)
            st.write("""
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
        with st.container(border=True):
            st.write("#### Confrontation de l'offre et de la demande")
            st.write("""
            Comme sur tous les marchés, le prix dépend de l’offre et de la demande. Si l’offre est supérieure à la demande, le prix diminue pour atteindre l’équilibre. À l’inverse, quand la demande est supérieure à l’offre, le prix augmente pour atteindre l’équilibre.
            """)
        with st.container(border=True):
            st.write("#### La liquidité des marchés financiers")
            st.write("""
            La fonction première de la Bourse est de permettre aux investisseurs d’acheter et de vendre leurs titres sur le marché secondaire.  
            C’est ce qu’on appelle la liquidité. 
            Un marché liquide est un marché sur lequel ont lieu beaucoup de transactions. 
            """)
    case _:
        st.write("### Work in Progress")


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
