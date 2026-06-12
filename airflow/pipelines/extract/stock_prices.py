import yfinance as yf
import pandas as pd
from db.connection import _postgres_connection_url
from sqlalchemy import create_engine, text
from config.ticker import get_cac40_tickers


def load_prices() -> None:
    df_list = []
    for ticker in get_cac40_tickers():
        data = yf.download(ticker, group_by="Ticker", period="5y", interval="1d")
        data = data.stack(level=0).rename_axis(["Date", "Ticker"]).reset_index(level=1)
        data["Ticker"] = ticker
        df_list.append(data.reset_index())
    df = pd.concat(df_list, ignore_index=True)

    # Ignore incomplete market rows to avoid storing NaN values in Postgres.
    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    df = df.dropna(subset=required_columns)

    if df.empty:
        return

    rows = df.to_dict(orient="records")

    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO raw.market_prices ("Date", "Open", "High", "Low", "Close", "Volume", "Ticker")
                VALUES (:Date, :Open, :High, :Low, :Close, :Volume, :Ticker)
                ON CONFLICT ("Date", "Ticker") DO NOTHING
                """),
            rows,
        )
