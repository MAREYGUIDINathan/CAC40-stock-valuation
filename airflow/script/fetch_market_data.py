import yfinance as yf

EDF = yf.Ticker("ENGI.PA")

df = EDF.history(period="5d", interval="1m")

df.to_parquet("airflow/data/edf_last5d_1min.parquet")