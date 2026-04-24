from __future__ import annotations

from datetime import datetime
import os

import pandas as pd
import yfinance as yf
from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text
from pipelines.extract.stock_prices import load_prices
from pipelines.extract.balance_sheet import load_balance_sheet



with DAG(
    dag_id="cac40_valuation",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["market-data", "yfinance"],
) as dag:
    # --- Layer 1: Extract & Load ---
    t_prices = PythonOperator(
        task_id="load_stock_prices",
        python_callable=load_prices,
    )
    t_balance_sheet = PythonOperator(
        task_id="load_balance_sheet",
        python_callable=load_balance_sheet,
    )
