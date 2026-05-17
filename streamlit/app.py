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


RATIO_LABEL_TO_API = {
    "P/E Ratio": "PE",
    "P/S Ratio": "PS",
}

_SERIES_CONFIG = {
    None: {
        "y_col": "Close",
        "y_title": "Cours de clôture",
        "x_title": "Day",
        "secondary_col": None,
        "secondary_title": None,
        "empty_message": "Aucune donnée disponible pour la sélection.",
    },
    "PE": {
        "y_col": "PE",
        "y_title": "P/E Ratio",
        "x_title": "Date",
        "secondary_col": "EPS",
        "secondary_title": "BPA (EPS)",
        "empty_message": "Aucune donnée de ratio disponible pour la sélection.",
    },
    "PS": {
        "y_col": "PS",
        "y_title": "P/S Ratio",
        "x_title": "Date",
        "secondary_col": "SPS",
        "secondary_title": "CA par action (SPS)",
        "empty_message": "Aucune donnée de ratio disponible pour la sélection.",
    },
}


def _series_config(ratio: str | None = None) -> dict:
    return _SERIES_CONFIG[ratio]


@st.cache_data(ttl=60)
def create_ratios_df(
    period: str = "5Y",
    tickers: tuple[str, ...] = ("ENGI.PA",),
    ratio: str = "PE",
) -> pd.DataFrame:
    r = httpx.get(
        f"{API}/ratios",
        params={"period": period, "ratio": ratio, "tickers": list(tickers)},
        timeout=30.0,
    )
    if r.status_code != 200:
        return pd.DataFrame()
    return pd.DataFrame(r.json()["data"])


def line_chart(data_filtered: pd.DataFrame, ratio: str | None = None) -> None:
    """Line chart for prices (ratio=None) or PE/PS ratios."""
    cfg = _series_config(ratio)
    y_col = cfg["y_col"]

    if data_filtered.empty:
        st.info(cfg["empty_message"])
        return

    data = data_filtered.reset_index(drop=True)
    y_min = data[y_col].min()
    y_max = data[y_col].max()

    nearest = alt.selection_point(
        name=f"Select_{y_col}",
        encodings=["x", "y"],
        on="mouseover",
        empty=False,
        nearest=True,
    )

    tooltip = [
        alt.Tooltip("Ticker:N", title="Entreprise"),
        alt.Tooltip("Date:O", title="Date"),
        alt.Tooltip(f"{y_col}:Q", title=cfg["y_title"], format=".2f"),
    ]
    if cfg["secondary_col"]:
        tooltip.append(
            alt.Tooltip(
                f"{cfg['secondary_col']}:Q",
                title=cfg["secondary_title"],
                format=".2f",
            )
        )

    line = (
        alt.Chart(data)
        .mark_line(point=False)
        .encode(
            x=alt.X("Date:O", title=cfg["x_title"]),
            y=alt.Y(
                f"{y_col}:Q",
                title=cfg["y_title"],
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
            y=f"{y_col}:Q",
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

    points = (
        alt.Chart(data)
        .mark_point(color="red", size=70)
        .encode(
            x="Date:O",
            y=f"{y_col}:Q",
            color="Ticker:N",
            tooltip=tooltip,
        )
        .transform_filter(nearest)
    )

    st.altair_chart(alt.layer(line, selectors, rules, points), width="stretch")


def bar_chart(data_filtered: pd.DataFrame, ratio: str) -> None:
    """Bar chart of latest PE/PS value per ticker."""
    cfg = _series_config(ratio)
    y_col = cfg["y_col"]

    if data_filtered.empty:
        st.info(cfg["empty_message"])
        return

    latest = (
        data_filtered.sort_values("Date")
        .groupby("Ticker", as_index=False)
        .last()
    )

    tooltip = [
        alt.Tooltip("Ticker:N", title="Entreprise"),
        alt.Tooltip("Date:O", title="Dernière date"),
        alt.Tooltip(f"{y_col}:Q", title=cfg["y_title"], format=".2f"),
    ]
    if cfg["secondary_col"]:
        tooltip.append(
            alt.Tooltip(
                f"{cfg['secondary_col']}:Q",
                title=cfg["secondary_title"],
                format=".2f",
            )
        )

    chart = (
        alt.Chart(latest)
        .mark_bar()
        .encode(
            x=alt.X("Ticker:N", title="Entreprise", sort="-y"),
            y=alt.Y(f"{y_col}:Q", title=cfg["y_title"]),
            color=alt.Color("Ticker:N", title="Entreprise", legend=None),
            tooltip=tooltip,
        )
    )

    st.altair_chart(chart, width="stretch")


def _latest_per_ticker(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Ticker", *columns])
    return (
        df.sort_values("Date")
        .groupby("Ticker", as_index=False)
        .last()[["Ticker", *columns]]
    )


def build_summary_table(
    period: str,
    tickers: tuple[str, ...],
    prices_df: pd.DataFrame,
) -> pd.DataFrame:
    summary = pd.DataFrame({"Entreprise": list(tickers)})

    cours = _latest_per_ticker(prices_df, ["Close"]).rename(
        columns={"Ticker": "Entreprise", "Close": "Cours"}
    )
    pe = _latest_per_ticker(create_ratios_df(period, tickers, "PE"), ["PE", "EPS"]).rename(
        columns={"Ticker": "Entreprise", "PE": "P/E", "EPS": "EPS"}
    )
    ps = _latest_per_ticker(create_ratios_df(period, tickers, "PS"), ["PS", "SPS"]).rename(
        columns={"Ticker": "Entreprise", "PS": "P/S", "SPS": "SPS"}
    )

    for part in (cours, pe, ps):
        summary = summary.merge(part, on="Entreprise", how="left")

    return summary[["Entreprise", "Cours", "P/E", "P/S", "EPS", "SPS"]]


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

st.subheader(f"Évolution du cours")
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
with st.container():
    line_chart(data)

# Show ratio charts
ratio_api = RATIO_LABEL_TO_API.get(ratio)
if ratio_api and selected_tickers:
    ratios_df = create_ratios_df(
        st.session_state["period_filter"],
        tuple(selected_tickers),
        ratio_api,
    )
    st.subheader(f"Évolution du {ratio}")
    with st.container(horizontal=True):
        with st.container():
            st.caption("Courbe dans le temps")
            line_chart(ratios_df, ratio=ratio_api)
        with st.container():
            st.caption("Dernière valeur par entreprise")
            bar_chart(ratios_df, ratio_api)
elif ratio and ratio not in RATIO_LABEL_TO_API:
    st.info("Le Dividend Yield n'est pas encore disponible via l'API.")


if selected_tickers:
    st.subheader("Tableau récapitulatif")
    summary_df = build_summary_table(
        st.session_state["period_filter"],
        tuple(selected_tickers),
        data,
    )
    st.dataframe(
        summary_df,
        column_config={
            "Entreprise": st.column_config.TextColumn("Entreprise"),
            "Cours": st.column_config.NumberColumn("Cours", format="%.2f €"),
            "P/E": st.column_config.NumberColumn("P/E", format="%.2f"),
            "P/S": st.column_config.NumberColumn("P/S", format="%.2f"),
            "EPS": st.column_config.NumberColumn("EPS", format="%.2f"),
            "SPS": st.column_config.NumberColumn("SPS", format="%.2f"),
        },
        hide_index=True,
        width="stretch",
    )

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
