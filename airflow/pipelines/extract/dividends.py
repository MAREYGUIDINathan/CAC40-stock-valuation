import yfinance as yf
import pandas as pd
from db.connection import _postgres_connection_url
from sqlalchemy import create_engine, text
from config.ticker import get_cac40_tickers


def load_dividends() -> None:
    df_list = []
    for ticker in get_cac40_tickers():
        hist = yf.Ticker(ticker).history(period="5y", actions=True)
        if hist.empty or "Dividends" not in hist.columns:
            continue
        data = (
            hist[hist["Dividends"] > 0][["Dividends"]]
            .reset_index()
            .rename(columns={"Dividends": "Amount"})
        )
        data["Date"] = pd.to_datetime(data["Date"]).dt.tz_localize(None).dt.date
        data["Ticker"] = ticker
        df_list.append(data[["Date", "Ticker", "Amount"]])

    if not df_list:
        return

    df = pd.concat(df_list, ignore_index=True)
    df = df.dropna(subset=["Amount"])

    rows = df.to_dict(orient="records")

    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO raw.dividends ("Date", "Ticker", "Amount")
                VALUES (:Date, :Ticker, :Amount)
                ON CONFLICT ("Date", "Ticker") DO NOTHING
                """),
            rows,
        )
