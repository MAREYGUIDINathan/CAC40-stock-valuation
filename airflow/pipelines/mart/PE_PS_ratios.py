import pandas as pd
from db.connection import _postgres_connection_url
from sqlalchemy import create_engine, text


def create_pe_ps_ratios() -> None:
    engine = create_engine(_postgres_connection_url())
    df = pd.read_sql("""       
                    WITH eps AS (
                        SELECT 
                            bs."Date", 
                            bs."Ticker",
                            f."NetIncome"/bs."OrdinarySharesNumber" as "eps",
                            f."TotalRevenue"/bs."OrdinarySharesNumber" as "sps",
                            f."NetIncome",
                            bs."OrdinarySharesNumber"
                        FROM raw.balance_sheet AS bs
                        LEFT JOIN raw.financials as f
                        USING("Ticker", "Date")
                        ),
                    ttm_dividends AS (
                        SELECT
                            mp."Date",
                            mp."Ticker",
                            COALESCE(SUM(d."Amount"), 0) AS "ttm_dividend"
                        FROM raw.market_prices AS mp
                        LEFT JOIN raw.dividends AS d
                            ON d."Ticker" = mp."Ticker"
                            AND d."Date" > mp."Date" - INTERVAL '1 year'
                            AND d."Date" <= mp."Date"
                        GROUP BY mp."Date", mp."Ticker"
                        )
                    SELECT 
                        mp."Date", 
                        mp."Ticker", 
                        mp."Close",
                        mp."Close" / eps."eps" as "PE",
                        mp."Close" / eps."sps" as "PS",
                        eps."sps",
                        eps."eps",
                        CASE
                            WHEN mp."Close" > 0
                            THEN (ttm."ttm_dividend" / mp."Close") * 100
                            ELSE NULL
                        END AS "dividend_yield"
                    FROM raw.market_prices AS mp
                    LEFT JOIN eps
                    ON 
                        mp."Ticker" = eps."Ticker" AND
                        extract(year from mp."Date") = extract(year from eps."Date") + 1
                    LEFT JOIN ttm_dividends AS ttm
                    ON mp."Date" = ttm."Date" AND mp."Ticker" = ttm."Ticker"
                    WHERE eps."eps" <> 'NaN' 
                    """,
                    engine)
    
    rows = df.to_dict(orient="records")
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO mart.pe_ps_ratios ("Date", "Ticker", "PE", "PS", "sps", "eps", "dividend_yield")
                VALUES (:Date, :Ticker, :PE, :PS, :sps, :eps, :dividend_yield)
                ON CONFLICT ("Date", "Ticker") DO UPDATE SET
                    "PE" = EXCLUDED."PE",
                    "PS" = EXCLUDED."PS",
                    "sps" = EXCLUDED."sps",
                    "eps" = EXCLUDED."eps",
                    "dividend_yield" = EXCLUDED."dividend_yield"
                """),
            rows
        )