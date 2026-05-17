import yfinance as yf
import pandas as pd
from db.connection import _postgres_connection_url
from sqlalchemy import create_engine, text
from config.ticker import tickerStrings

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
                        )
                    SELECT 
                        mp."Date", 
                        mp."Ticker", 
                        mp."Close",
                        mp."Close" / eps."eps" as "PE",
                        mp."Close" / eps."sps" as "PS",
                        eps."sps",
                        eps."eps"
                    FROM raw.market_prices AS mp
                    LEFT JOIN eps
                    ON 
                        mp."Ticker" = eps."Ticker" AND
                        extract(year from mp."Date") = extract(year from eps."Date")
                    WHERE eps."eps" <> 'NaN' 
                    """,
                    engine)
    
    rows = df.to_dict(orient="records")
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO mart.pe_ps_ratios ("Date", "Ticker", "PE", "PS", "sps", "eps")
                VALUES (:Date, :Ticker, :PE, :PS, :sps, :eps)
                ON CONFLICT ("Date", "Ticker") DO NOTHING
                """),
            rows
        )