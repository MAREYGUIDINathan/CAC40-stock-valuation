import yfinance as yf
import pandas as pd
from db.connection import _postgres_connection_url
from sqlalchemy import create_engine, text
from config.ticker import tickerStrings


def load_financials() -> None:
    df_list = []
    for ticker in tickerStrings:
        data = yf.Ticker(ticker).get_financials().T
        data["Ticker"] = ticker
        df_list.append(data.reset_index(names="Date"))
    df = pd.concat(df_list, ignore_index=True)

    if df.empty:
        return

    rows = df.to_dict(orient="records")

    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO raw.financials ("Date", "Ticker", "NetIncome", "TotalRevenue", "OperatingIncome")
                VALUES (:Date, :Ticker, :NetIncome, :TotalRevenue, :OperatingIncome)
                ON CONFLICT ("Date", "Ticker") DO NOTHING
                """),
            rows,
        )