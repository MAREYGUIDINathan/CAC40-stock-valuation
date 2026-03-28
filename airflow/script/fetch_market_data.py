import yfinance as yf
from datetime import datetime

EDF = yf.Ticker("ENGI.PA")

df = EDF.history(period="3y", interval="1d")

today_date = datetime.today()

df.to_parquet(f"airflow/data/engie{today_date}.parquet")