import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text

app = FastAPI()

PERIODS = {
    "1m": timedelta(days=30),
    "6m": timedelta(days=180),
    "1y": timedelta(days=365),
    "5y": timedelta(days=365 * 5),
}


def _postgres_connection_url() -> str:
    user = os.getenv("POSTGRES_USER", "airflow")
    password = os.getenv("POSTGRES_PASSWORD", "airflow")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "airflow")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


@app.get("/")
def get_ticker(period: str, ticker: str = "ENGI.PA"):
    today = datetime.today().date()

    if period == "CY":
        start_date = today.replace(month=1, day=1)
    else:
        if period not in PERIODS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period '{period}'. Allowed values: {', '.join(['CY', *PERIODS.keys()])}",
            )
        start_date = today - PERIODS[period]

    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                SELECT "Date", "Open", "High", "Low", "Close", "Volume", "Ticker"
                FROM raw.market_prices
                WHERE "Ticker" = :ticker
                  AND "Date" BETWEEN :start_date AND :end_date
                ORDER BY "Date" ASC
                """),
            {"ticker": ticker, "start_date": start_date, "end_date": today},
        )
        records = [dict(row) for row in result.mappings()]
        for record in records:
            record["Date"] = record["Date"].isoformat()

    return {
        "ticker": ticker,
        "period": period,
        "data": records,
    }


def _get_unique_tickers() -> list:
    """Fetch all unique tickers from the database."""
    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                SELECT DISTINCT "Ticker"
                FROM raw.market_prices
                ORDER BY "Ticker" ASC
                """)
        )
        tickers = [row[0] for row in result.fetchall()]
    return tickers


@app.get("/tickers")
def get_tickers():
    """Return list of unique tickers available in the database."""
    try:
        tickers = _get_unique_tickers()
        return {"tickers": tickers}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching tickers: {str(e)}"
        )


@app.get("/metrics")
def get_metrics(period: str, ticker: str = "ENGI.PA"):
    """Calculate and return price metrics for a given period and ticker."""
    today = datetime.today().date()

    if period == "CY":
        start_date = today.replace(month=1, day=1)
    else:
        if period not in PERIODS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period '{period}'. Allowed values: {', '.join(['CY', *PERIODS.keys()])}",
            )
        start_date = today - PERIODS[period]

    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                SELECT "Close", "Volume"
                FROM raw.market_prices
                WHERE "Ticker" = :ticker
                  AND "Date" BETWEEN :start_date AND :end_date
                ORDER BY "Date" ASC
                """),
            {"ticker": ticker, "start_date": start_date, "end_date": today},
        )
        records = [dict(row) for row in result.mappings()]

    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for ticker '{ticker}' in the given period"
        )

    current_price = records[-1]["Close"]
    previous_price = records[0]["Close"]
    percentage_change = ((current_price - previous_price) / previous_price) * 100
    average_volume = sum(record["Volume"] for record in records) / len(records)

    return {
        "current_price": float(current_price),
        "percentage_change": float(percentage_change),
        "average_volume": float(average_volume)
    }
