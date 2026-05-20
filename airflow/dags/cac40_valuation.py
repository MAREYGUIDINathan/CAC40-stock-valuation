from __future__ import annotations

from datetime import datetime
import os

import pandas as pd
import yfinance as yf
from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text
from pipelines.extract.cac40 import load_cac40
from pipelines.extract.stock_prices import load_prices
from pipelines.extract.balance_sheet import load_balance_sheet
from pipelines.extract.financials import load_financials
from pipelines.extract.dividends import load_dividends
from pipelines.mart.PE_PS_ratios import create_pe_ps_ratios


with DAG(
    dag_id="cac40_valuation",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["market-data", "yfinance"],
) as dag:
    # --- Layer 1: Extract & Load ---
    t_cac40 = PythonOperator(
        task_id="load_cac40",
        python_callable=load_cac40,
    )
    t_prices = PythonOperator(
        task_id="load_stock_prices",
        python_callable=load_prices,
    )
    t_balance_sheet = PythonOperator(
        task_id="load_balance_sheet",
        python_callable=load_balance_sheet,
    )
    t_financials = PythonOperator(
        task_id="load_financials",
        python_callable=load_financials,
    )
    t_dividends = PythonOperator(
        task_id="load_dividends",
        python_callable=load_dividends,
    )
    t_pe_ps = PythonOperator(
        task_id="create_pe_ps_ratios",
        python_callable=create_pe_ps_ratios,
    )

    t_cac40 >> [t_prices, t_balance_sheet, t_financials, t_dividends] >> t_pe_ps