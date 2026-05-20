import os
from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import bindparam, create_engine, text

app = FastAPI()

PERIODS = {
    "1M": timedelta(days=30),
    "6M": timedelta(days=180),
    "1Y": timedelta(days=365),
    "5Y": timedelta(days=365 * 5),
}


def _postgres_connection_url() -> str:
    user = os.getenv("POSTGRES_USER", "airflow")
    password = os.getenv("POSTGRES_PASSWORD", "airflow")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "airflow")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


@app.get("/")
def get_ticker(
    period: str,
    ticker: Annotated[list[str], Query()] = ["ENGI.PA"],
):
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

    tickers = list(dict.fromkeys(ticker))
    if not tickers:
        return {"tickers": [], "period": period, "data": []}

    query = text("""
        SELECT mp."Date", c."Nom" as "Ticker", mp."Close"
        FROM raw.market_prices AS mp
        LEFT JOIN raw.cac40 AS c ON mp."Ticker" = c."Ticker"
        WHERE mp."Ticker" IN :tickers
          AND mp."Date" BETWEEN :start_date AND :end_date
        ORDER BY mp."Ticker" ASC, mp."Date" ASC
        """).bindparams(bindparam("tickers", expanding=True))

    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        result = connection.execute(
            query,
            {"tickers": tickers, "start_date": start_date, "end_date": today},
        )
        records = [dict(row) for row in result.mappings()]
        for record in records:
            record["Date"] = record["Date"].isoformat()

    return {
        "tickers": tickers,
        "period": period,
        "data": records,
    }


def _get_unique_tickers() -> list[dict]:
    """Fetch all unique tickers and their names from the database."""
    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        result = connection.execute(text("""
                SELECT DISTINCT "Ticker", "Nom"
                FROM raw.cac40
                ORDER BY "Nom" ASC
                """))
        # result.fetchall() produces a list of tuples; use indices, not keys.
        tickers = [{"ticker": row[0], "name": row[1]} for row in result.fetchall()]
    return tickers


@app.get("/tickers")
def get_tickers():
    """Return list of unique tickers and their names available in the database."""
    try:
        tickers = _get_unique_tickers()
        return {"tickers": tickers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tickers: {str(e)}")


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
                SELECT mp."Close", mp."Volume", c."Nom" as Ticker
                FROM raw.market_prices AS mp
                LEFT JOIN raw.cac40 AS c ON mp."Ticker" = c."Ticker"
                WHERE mp."Ticker" = :ticker
                  AND mp."Date" BETWEEN :start_date AND :end_date
                ORDER BY mp."Date" ASC
                """),
           
            {"ticker": ticker, "start_date": start_date, "end_date": today},
        )
        records = [dict(row) for row in result.mappings()]

    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for ticker '{ticker}' in the given period",
        )

    current_price = records[-1]["Close"]
    previous_price = records[0]["Close"]
    percentage_change = ((current_price - previous_price) / previous_price) * 100
    average_volume = sum(record["Volume"] for record in records) / len(records)

    return {
        "current_price": float(current_price),
        "percentage_change": float(percentage_change),
        "average_volume": float(average_volume),
    }


@app.get("/ratios")
def get_ratios(
    period: str,
    ratio: Literal["PE", "PS"],
    tickers: Annotated[list[str], Query()] = ["ENGI.PA"],
):
    """Return PE/EPS or PS/SPS series from mart.pe_ps_ratios."""
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

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"tickers": [], "period": period, "ratio": ratio, "data": []}

    if ratio == "PE":
        columns = '"Date", "Nom" as "Ticker", "PE", "eps"'
    else:
        columns = '"Date", "Nom" as "Ticker", "PS", "sps"'

    query = text(f"""
        SELECT {columns}
        FROM mart.pe_ps_ratios
        JOIN raw.cac40 ON mart.pe_ps_ratios."Ticker" = raw.cac40."Ticker"
        WHERE mart.pe_ps_ratios."Ticker" IN :tickers
          AND mart.pe_ps_ratios."Date" BETWEEN :start_date AND :end_date
        ORDER BY mart.pe_ps_ratios."Ticker" ASC, mart.pe_ps_ratios."Date" ASC
        """).bindparams(bindparam("tickers", expanding=True))
   

    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        result = connection.execute(
            query,
            {"tickers": tickers, "start_date": start_date, "end_date": today},
        )
        records = [dict(row) for row in result.mappings()]
        for record in records:
            record["Date"] = record["Date"].isoformat()
            if ratio == "PE":
                record["EPS"] = record.pop("eps")
            else:
                record["SPS"] = record.pop("sps")

    return {
        "tickers": tickers,
        "period": period,
        "ratio": ratio,
        "data": records,
    }
