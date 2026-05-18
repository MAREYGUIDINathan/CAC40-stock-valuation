import yfinance as yf
import pandas as pd
from db.connection import _postgres_connection_url
from sqlalchemy import create_engine, text
from config.ticker import get_cac40_tickers


def load_balance_sheet() -> None:
    df_list = []
    for ticker in get_cac40_tickers():
        data = yf.Ticker(ticker).get_balance_sheet().T
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
                INSERT INTO raw.balance_sheet ("Date", "Ticker", "OrdinarySharesNumber", "TotalDebt", "CommonStockEquity", "CashAndCashEquivalents")
                VALUES (:Date, :Ticker, :OrdinarySharesNumber, :TotalDebt, :CommonStockEquity, :CashAndCashEquivalents)
                ON CONFLICT ("Date", "Ticker") DO NOTHING
                """),
            rows,
        )