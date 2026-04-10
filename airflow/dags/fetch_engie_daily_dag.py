from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yfinance as yf
from airflow import DAG
from airflow.operators.python import PythonOperator


def fetch_engie_data() -> None:
    ticker = yf.Ticker("ENGI.PA")
    df = ticker.history(period="3y", interval="1d")

    output_dir = Path("/opt/airflow/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_dir / "engie.parquet")


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
