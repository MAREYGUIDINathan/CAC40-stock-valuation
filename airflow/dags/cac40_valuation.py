from __future__ import annotations

from datetime import datetime
import os

import pandas as pd
import yfinance as yf
from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text

tickerStrings = [
    "AC.PA",    # Accor
    "ADP.PA",   # Aéroports de Paris
    "AIR.PA",   # Airbus
    "ALLO.PA",  # Alstom
    "MT.PA",    # ArcelorMittal
    "MC.PA",    # LVMH/Arnault
    "CS.PA",    # AXA
    "BNP.PA",   # BNP Paribas
    "EN.PA",    # Bouygues
    "BVI.PA",   # Bureau Veritas
    "CAP.PA",   # Capgemini
    "CA.PA",    # Carrefour
    "ACA.PA",   # Crédit Agricole
    "DSY.PA",   # Dassault Systèmes
    "DANON.PA", # Danone
    "EDF.PA",   # EDF
    "ENGI.PA",  # Engie
    "EL.PA",    # Essilor Luxottica
    "ERA.PA",   # Eramet
    "ERF.PA",   # Eurofins
    "GET.PA",   # Getlink
    "RMS.PA",   # Hermès
    "IPN.PA",   # Ipsen
    "KER.PA",   # Kering
    "LI.PA",    # Klepierre
    "LR.PA",    # Legrand
    "OR.PA",    # L'Oréal
    "ML.PA",    # Michelin
    "ORAN.PA",  # Orange
    "RI.PA",    # Pernod Ricard
    "PUB.PA",   # Publicis
    "RNO.PA",   # Renault   
    "RXL.PA",   # Rexel
    "SAF.PA",   # Safran
    "SGO.PA",   # Saint-Gobain
    "SNPI.PA",  # Sanofi
    "SU.PA",    # Schneider Electric
    "GLE.PA",   # Société Générale
    "SOD.PA",   # Sodexo
    "STM.PA",   # STMicroelectronics
]


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
