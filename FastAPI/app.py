from datetime import datetime, timedelta
from fastapi import FastAPI
import pandas as pd


app = FastAPI()


DATA_PATH = "airflow/data/engie.parquet"


PERIODS = {
    "1m": timedelta(days=30),
    "6m": timedelta(days=180),
    "1y": timedelta(days=365),
    "5y": timedelta(days=365*5)
}


@app.get("/")
def get_ticker(period: str):
    today = datetime.today().date()
    end_date = str(today)
    df = pd.read_parquet("./airflow/data/engie.parquet")

    if period == "CY":
        start_date = str(today.replace(month=1,day=1))
    else:
        start_date = str(today - PERIODS[period])

    df = df.loc[start_date:end_date]


    return {
        "ticker": "ENGI",
        "data": df.reset_index().to_dict(orient="records")
    }