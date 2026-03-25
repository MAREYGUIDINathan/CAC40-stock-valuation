from altair.vegalite import Data
import streamlit as st
import pandas as pd
from datetime import datetime


@st.cache_data
def create_table() -> pd.DataFrame:
    data = pd.read_parquet("airflow/data/edf_last5d_1min.parquet")
    return data


data = create_table()

data_filtered = data.loc["2026-03-25":"2026-03-26"]

st.title("Begginer Introduction to Technical Analysis of the Stock Market")

st.line_chart(data=data_filtered, y="Close")
st.table(data_filtered)
