import math
import os
from datetime import date, datetime, timedelta
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

WEEKLY_PERIODS = frozenset({"6M", "CY", "1Y", "5Y"})


def _sanitize_record(record: dict) -> dict:
    for key, value in record.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            record[key] = None
    return record


def _postgres_connection_url() -> str:
    user = os.getenv("POSTGRES_USER", "airflow")
    password = os.getenv("POSTGRES_PASSWORD", "airflow")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "airflow")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def _period_bounds(period: str) -> tuple[date, date]:
    today = datetime.today().date()
    if period == "CY":
        return today.replace(month=1, day=1), today
    if period not in PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Allowed values: {', '.join(['CY', *PERIODS.keys()])}",
        )
    return today - PERIODS[period], today


def _weekly_resolution(period: str) -> bool:
    return period in WEEKLY_PERIODS


@app.get("/")
def get_ticker(
    period: str,
    ticker: Annotated[list[str], Query()] = ["ENGI.PA"],
):
    start_date, end_date = _period_bounds(period)
    weekly = _weekly_resolution(period)

    tickers = list(dict.fromkeys(ticker))
    if not tickers:
        return {"tickers": [], "period": period, "resolution": "weekly" if weekly else "daily", "data": []}

    if weekly:
        query = text("""
            WITH ranked AS (
                SELECT
                    mp."Date",
                    c."Nom" AS "Ticker",
                    mp."Close",
                    ROW_NUMBER() OVER (
                        PARTITION BY mp."Ticker", date_trunc('week', mp."Date"::timestamp)
                        ORDER BY mp."Date" DESC
                    ) AS rn
                FROM raw.market_prices AS mp
                LEFT JOIN raw.cac40 AS c ON mp."Ticker" = c."Ticker"
                WHERE mp."Ticker" IN :tickers
                  AND mp."Date" BETWEEN :start_date AND :end_date
            )
            SELECT "Date", "Ticker", "Close"
            FROM ranked
            WHERE rn = 1
            ORDER BY "Ticker" ASC, "Date" ASC
            """).bindparams(bindparam("tickers", expanding=True))
    else:
        query = text("""
            SELECT mp."Date", c."Nom" AS "Ticker", mp."Close"
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
            {"tickers": tickers, "start_date": start_date, "end_date": end_date},
        )
        records = [dict(row) for row in result.mappings()]
        for record in records:
            record["Date"] = record["Date"].isoformat()

    return {
        "tickers": tickers,
        "period": period,
        "resolution": "weekly" if weekly else "daily",
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
    start_date, end_date = _period_bounds(period)

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
           
            {"ticker": ticker, "start_date": start_date, "end_date": end_date},
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
    ratio: Literal["PE", "PS", "DY"],
    tickers: Annotated[list[str], Query()] = ["ENGI.PA"],
):
    """Return PE/EPS, PS/SPS, or dividend yield series from mart.pe_ps_ratios."""
    start_date, end_date = _period_bounds(period)
    weekly = _weekly_resolution(period)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {
            "tickers": [],
            "period": period,
            "ratio": ratio,
            "resolution": "weekly" if weekly else "daily",
            "data": [],
        }

    if ratio == "PE":
        select_cols = 'r."Date", c."Nom" AS "Ticker", r."PE", r."eps"'
        weekly_select = '"Date", "Ticker", "PE", "eps"'
    elif ratio == "PS":
        select_cols = 'r."Date", c."Nom" AS "Ticker", r."PS", r."sps"'
        weekly_select = '"Date", "Ticker", "PS", "sps"'
    else:
        select_cols = 'r."Date", c."Nom" AS "Ticker", r."dividend_yield"'
        weekly_select = '"Date", "Ticker", "dividend_yield"'

    if weekly:
        query = text(f"""
            WITH ranked AS (
                SELECT
                    {select_cols},
                    ROW_NUMBER() OVER (
                        PARTITION BY c."Nom", date_trunc('week', r."Date"::timestamp)
                        ORDER BY r."Date" DESC
                    ) AS rn
                FROM mart.pe_ps_ratios AS r
                JOIN raw.cac40 AS c ON r."Ticker" = c."Ticker"
                WHERE r."Ticker" IN :tickers
                  AND r."Date" BETWEEN :start_date AND :end_date
            )
            SELECT {weekly_select}
            FROM ranked
            WHERE rn = 1
            ORDER BY "Ticker" ASC, "Date" ASC
            """).bindparams(bindparam("tickers", expanding=True))
    else:
        query = text(f"""
            SELECT {select_cols}
            FROM mart.pe_ps_ratios AS r
            JOIN raw.cac40 AS c ON r."Ticker" = c."Ticker"
            WHERE r."Ticker" IN :tickers
              AND r."Date" BETWEEN :start_date AND :end_date
            ORDER BY c."Nom" ASC, r."Date" ASC
            """).bindparams(bindparam("tickers", expanding=True))

    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        result = connection.execute(
            query,
            {"tickers": tickers, "start_date": start_date, "end_date": end_date},
        )
        records = [dict(row) for row in result.mappings()]
        for record in records:
            record["Date"] = record["Date"].isoformat()
            if ratio == "PE":
                record["EPS"] = record.pop("eps")
            elif ratio == "PS":
                record["SPS"] = record.pop("sps")
            else:
                record["DividendYield"] = record.pop("dividend_yield")
            _sanitize_record(record)

    return {
        "tickers": tickers,
        "period": period,
        "ratio": ratio,
        "resolution": "weekly" if weekly else "daily",
        "data": records,
    }


@app.get("/summary")
def get_summary():
    """Return latest valuation metrics for all CAC 40 companies."""
    engine = create_engine(_postgres_connection_url())
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                SELECT
                    "Ticker",
                    "Nom",
                    "Cours",
                    "PE",
                    "PS",
                    "EPS",
                    "SPS",
                    "dividend_yield",
                    "as_of_date"
                FROM mart.valuation_summary
                ORDER BY "Nom" ASC
                """)
        )
        records = [dict(row) for row in result.mappings()]

    for record in records:
        if record.get("as_of_date"):
            record["as_of_date"] = record["as_of_date"].isoformat()
        record["DividendYield"] = record.pop("dividend_yield")
        _sanitize_record(record)

    return {"data": records}
