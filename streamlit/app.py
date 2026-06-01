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
    tickers_info = httpx.get(f"{API}/tickers").json()["tickers"]
    names = [ticker["name"] for ticker in tickers_info]
    mapping_name_ticker = {}
    for ticker in tickers_info:
        mapping_name_ticker[ticker["name"]] = ticker["ticker"]
    return [mapping_name_ticker, names] 


RATIO_LABEL_TO_API = {
    "P/E Ratio": "PE",
    "P/S Ratio": "PS",
    "Dividend Yield": "DY",
}

_SERIES_CONFIG = {
    None: {
        "y_col": "Close",
        "y_title": "Market Price",
        "x_title": "Day",
        "secondary_col": None,
        "secondary_title": None,
        "empty_message": "No data available for the selection.",
    },
    "PE": {
        "y_col": "PE",
        "y_title": "P/E Ratio",
        "x_title": "Date",
        "secondary_col": "EPS",
        "secondary_title": "EPS",
        "empty_message": "No data available for the selection.",
    },
    "PS": {
        "y_col": "PS",
        "y_title": "P/S Ratio",
        "x_title": "Date",
        "secondary_col": "PS",
        "secondary_title": "PS",
        "empty_message": "No data available for the selection.",
    },
    "DY": {
        "y_col": "DividendYield",
        "y_title": "Dividend Yield (%)",
        "x_title": "Date",
        "secondary_col": None,
        "secondary_title": None,
        "empty_message": "No data available for the selection.",
    },
}


RATIO_HELP = {
    "P/E Ratio ?": (
        "**P/E (Price / Earning)** — How much earning is made by stock compared to the price of the stock.\n\n"
        "**Formula :** \n\n"
        "P/E = Market price ÷ Earning per share"
    ),
    "P/S Ratio ?": (
        "**P/S (Price / Sales)** — How much sales is made by stock compared to the price of the stock \n\n"
        "**Formula :** \n\n"
        "P/S = Market price ÷ Sales per share"
    ),
    "Dividend Yield ?": (
        "**Dividend Yield** — How much dividend you get by having stock\n\n"
        "**Formula :** \n\n"
        "(n-1 Dividends ÷ Price) × 100"
    ),
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
        alt.Tooltip("Ticker:N", title="Company"),
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
            color=alt.Color("Ticker:N", title="Company"),
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
        alt.Tooltip("Ticker:N", title="Company"),
        alt.Tooltip("Date:O", title="Last date"),
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
            x=alt.X("Ticker:N", title="Company", sort="-y"),
            y=alt.Y(f"{y_col}:Q", title=cfg["y_title"]),
            color=alt.Color("Ticker:N", title="Company", legend=None),
            tooltip=tooltip,
        )
    )

    st.altair_chart(chart, width="stretch")


@st.cache_data(ttl=60)
def fetch_summary_df() -> pd.DataFrame:
    r = httpx.get(f"{API}/summary", timeout=30.0)
    if r.status_code != 200:
        return pd.DataFrame()
    data = r.json().get("data", [])
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    return df.rename(
        columns={
            "Nom": "Company",
            "Cours": "Market price",
            "PE": "P/E",
            "PS": "P/S",
            "DividendYield": "Dividend Yield (%)",
        }
    )[["Company", "Market price", "P/E", "P/S", "Dividend Yield (%)", "EPS", "SPS", "as_of_date"]]


ticker_mapping, company_names = get_tickers_options()
default_companies = company_names[:3]

with st.sidebar:
    st.header("val.cac40")

    st.session_state["ticker_selected"] = st.pills(
        "COMPANY",
        company_names,
        selection_mode="multi",
        default=default_companies,
        key="entreprises_pills",
    ) or []

    st.session_state["period_filter"] = st.pills(
        "PERIOD",
        ["1M", "6M", "CY", "1Y", "5Y"],
        selection_mode="single",
        required=True,
        default="5Y",
    )

    ratio = st.pills(
        "RATIO",
        ["P/E Ratio", "P/S Ratio", "Dividend Yield"],
        selection_mode="single",
        required=True,
        default="P/E Ratio",
    )

    st.markdown(
    """
<hr style="margin-top:50px;">

""",
    unsafe_allow_html=True,
)
    st.session_state["explanation"] = st.pills(
        "WHAT IS",
        ["P/E Ratio ?", "P/S Ratio ?", "Dividend Yield ?"],
        selection_mode="single",
        required=True,
        default="P/E Ratio ?"
    )
    st.container(border=True).markdown(RATIO_HELP[st.session_state["explanation"]])


selected_companies = st.session_state.get("ticker_selected") or []
if isinstance(selected_companies, str):
    selected_companies = [selected_companies]

# Show Title
st.title("Valuation of CAC 40 stocks", text_alignment="left")

période = {"1M": "1 Month", "6M": "6 Month", "CY": "Current Year", "1Y": "1 Year", "5Y": "5 Year"}

if len(selected_companies) > 1:
    st.write(
    f"{len(selected_companies)} companies selected  ·  {ratio}  ·  {période[st.session_state['period_filter']]} "
    )
else:
    st.write(
    f"{len(selected_companies)} company selected  ·  {ratio}  ·  {période[st.session_state['period_filter']]} "
    ) 

if not selected_companies:
    st.warning("Select at least one company")
else:
    selected_tickers = [ticker_mapping[entreprise] for entreprise in selected_companies]
    data = create_df(st.session_state["period_filter"], tuple(selected_tickers))

    st.subheader("Market price evolution")
    with st.container(horizontal=True):
        for entreprise in selected_companies:
            metrics_response = httpx.get(
                f"{API}/metrics",
                params={
                    "period": st.session_state["period_filter"],
                    "ticker": ticker_mapping[entreprise],
                },
            )

            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
                current_price = metrics["current_price"]
                percentage_change = metrics["percentage_change"]

                st.metric(
                    f"{entreprise} market price",
                    f"{current_price:.2f}€",
                    f"{percentage_change:+.2f}%",
                    border=True,
                )

    with st.container(border=True):
        line_chart(data)

    ratio_api = RATIO_LABEL_TO_API.get(ratio)
    if ratio_api:
        ratios_df = create_ratios_df(
            st.session_state["period_filter"],
            tuple(selected_tickers),
            ratio_api,
        )
        st.subheader(f"{ratio} evolution")
        with st.container(horizontal=True):
            with st.container(border=True):
                st.caption("ratio evolution")
                line_chart(ratios_df, ratio=ratio_api)
            with st.container(border=True):
                st.caption("Last value by company")
                bar_chart(ratios_df, ratio_api)
st.subheader("Summary table — CAC 40")
summary_df = fetch_summary_df()
if summary_df.empty:
    st.info("Aucune donnée récapitulative disponible. Lancez le DAG Airflow (create_valuation_summary).")
else:
    st.dataframe(
        summary_df.drop(columns=["as_of_date"], errors="ignore"),
        column_config={
            "Company": st.column_config.TextColumn("Company"),
            "Market price": st.column_config.NumberColumn("Market price", format="%.2f €"),
            "P/E": st.column_config.NumberColumn("P/E", format="%.2f"),
            "P/S": st.column_config.NumberColumn("P/S", format="%.2f"),
            "Dividend Yield (%)": st.column_config.NumberColumn("Dividend Yield (%)", format="%.2f"),
            "EPS": st.column_config.NumberColumn("EPS", format="%.2f"),
            "SPS": st.column_config.NumberColumn("SPS", format="%.2f"),
        },
        hide_index=True,
        width="stretch",
    )
    if "as_of_date" in summary_df.columns and summary_df["as_of_date"].notna().any():
        st.caption(f"Data of {summary_df['as_of_date'].max()}")

# -------------------------------------
#  Footer
# -------------------------------------
        
st.markdown(
    """
<hr style="margin-top:50px;">

<div style="text-align: left; font-size: 0.9em; margin-top:30px">
© 2026 MAREY--GUIDI Nathan — Cac40-stock-valuation <br>
built with Streamlit, Airflow & Fast API<br>
<i>For educational purposes only — not financial advice</i>
</div>
""",
    unsafe_allow_html=True,
)
