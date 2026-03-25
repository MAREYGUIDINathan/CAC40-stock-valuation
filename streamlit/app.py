from altair.vegalite import Data
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime


@st.cache_data
def create_table() -> pd.DataFrame:
    data = pd.read_parquet("airflow/data/edf_last5d_1min.parquet")
    return data


data = create_table()

data_filtered = data.loc["2026-03-25":"2026-03-26"]

#Title
st.title("Begginer Introduction to Technical Analysis of the Stock Market")

# Affichage d'un graphique centré sur la moyenne avec une échelle pertinente (Close vs. Datetime)

# On ajuste l'échelle pour être autour de la moyenne
y_min = data_filtered["Close"].min()
y_max = data_filtered["Close"].max()

# Utilise selection_point pour la sélection "hover"
nearest = alt.selection_point(
    name="Select",
    encodings=["x"],
    on="mouseover",
    empty=False,
    nearest=True
)

# Line chart
line = alt.Chart(data_filtered.reset_index()).mark_line().encode(
    x=alt.X("Datetime:T", title="Heure"),
    y=alt.Y(
        "Close:Q",
        title="Cours de clôture",
        scale=alt.Scale(domain=[y_min, y_max])
    )
)

# Sélecteurs transparents pour la détection du hover
selectors = alt.Chart(data_filtered.reset_index()).mark_point(color='transparent').encode(
    x=alt.X('Datetime:T', axis=alt.Axis(format='%Hh%M', title='Heure')),
    y='Close:Q',
).add_params(
    nearest
)

# Droite verticale qui suit la souris (sélection)
rules = alt.Chart(data_filtered.reset_index()).mark_rule(color="gray").encode(
    x="Datetime:T",
).transform_filter(
    nearest
)

# Afficher un point sur la courbe sous la souris
points = alt.Chart(data_filtered.reset_index()).mark_point(
    color='red',
    size=70
).encode(
    x='Datetime:T',
    y='Close:Q'
).transform_filter(
    nearest
)

# Combine
line_chart = alt.layer(
    line,
    selectors,
    rules,
    points
).properties(
    title="Evolution du cours de clôture (centré sur la moyenne, échelle pertinente)"
)

st.altair_chart(line_chart, use_container_width=True)


#table
st.table(data_filtered.tail())

