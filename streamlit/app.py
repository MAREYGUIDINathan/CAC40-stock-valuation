import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime


@st.cache_data
def create_table() -> pd.DataFrame:
    data = pd.read_parquet("airflow/data/engie2026-03-28 11:40:42.696876.parquet")
    return data

def line_chart(data_filtered):
    # Affichage d'un graphique centré sur la moyenne avec une échelle pertinente (Close vs. Datetime)
    data = data_filtered.reset_index()
    y_min = data_filtered["Close"].min()
    y_max = data_filtered["Close"].max()

    # Utilise selection_point pour la sélection "hover"
    nearest = alt.selection_point(
        name="Select", encodings=["x"], on="mouseover", empty=False, nearest=True
    )

    # Line chart
    line = (
        alt.Chart(data)
        .mark_line()
        .encode(
            x=alt.X(
                "Date:T",
                title="Day",
                axis=alt.Axis(format="%m/%Y", labelAngle=90, tickCount="month")  
            ),
            y=alt.Y(
                "Close:Q", title="Cours de clôture", scale=alt.Scale(domain=[y_min, y_max])
            ),
            tooltip=[
                alt.Tooltip("Date:T", title="Date"),
                alt.Tooltip("Close:Q", title="Cours de clôture")
            ]
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
    line_chart = alt.layer(line, selectors, rules, points).properties(
        title="Evolution du cours de clôture des actions d'Engie"
    )

    st.altair_chart(line_chart, width="stretch")

data = create_table()

data_filtered = data

# Show Title
st.title("Beginner Introduction to Stock Market")

# Show line chart
line_chart(data_filtered)

# Show Table
st.table(data_filtered.head())
