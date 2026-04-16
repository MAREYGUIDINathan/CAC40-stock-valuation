from __future__ import annotations

from datetime import datetime
import os

import pandas as pd
import yfinance as yf
from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text

tickerStrings = ["ENGI.PA", "AIR.PA"]


def _postgres_connection_url() -> str:
    user = os.getenv("POSTGRES_USER", "airflow")
    password = os.getenv("POSTGRES_PASSWORD", "airflow")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "airflow")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def fetch_engie_data() -> None:
    df_list = []
    for ticker in tickerStrings:
        data = yf.download(
            ticker, group_by="Ticker", period="5y", interval="1d"
        )
        data = (
            data.stack(level=0)
            .rename_axis(["Date", "Ticker"])
            .reset_index(level=1)
        )
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
                INSERT INTO market_data.daily_prices ("Date", "Open", "High", "Low", "Close", "Volume", "Ticker")
                VALUES (:Date, :Open, :High, :Low, :Close, :Volume, :Ticker)
                ON CONFLICT ("Date", "Ticker") DO NOTHING
                """),
            rows,
        )


with DAG(
    dag_id="fetch_engie_daily",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["market-data", "yfinance"],
) as dag:
    fetch_engie_task = PythonOperator(
        task_id="fetch_engie_data",
        python_callable=fetch_engie_data,
    )

    fetch_engie_task
