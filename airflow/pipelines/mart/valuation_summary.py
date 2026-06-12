import pandas as pd
from db.connection import _postgres_connection_url
from sqlalchemy import create_engine, text


def create_valuation_summary() -> None:
    engine = create_engine(_postgres_connection_url())
    df = pd.read_sql(
        """
        WITH latest_price AS (
            SELECT DISTINCT ON (mp."Ticker")
                mp."Ticker",
                mp."Close" AS "Cours",
                mp."Date" AS price_date
            FROM raw.market_prices AS mp
            ORDER BY mp."Ticker", mp."Date" DESC
        ),
        latest_ratios AS (
            SELECT DISTINCT ON (r."Ticker")
                r."Ticker",
                r."PE",
                r."PS",
                r."eps" AS "EPS",
                r."sps" AS "SPS",
                r."dividend_yield",
                r."Date" AS ratio_date
            FROM mart.pe_ps_ratios AS r
            ORDER BY r."Ticker", r."Date" DESC
        )
        SELECT
            c."Ticker",
            c."Nom",
            lp."Cours",
            lr."PE",
            lr."PS",
            lr."EPS",
            lr."SPS",
            lr."dividend_yield",
            GREATEST(lp.price_date, lr.ratio_date) AS "as_of_date"
        FROM raw.cac40 AS c
        LEFT JOIN latest_price AS lp ON c."Ticker" = lp."Ticker"
        LEFT JOIN latest_ratios AS lr ON c."Ticker" = lr."Ticker"
        ORDER BY c."Nom" ASC
        """,
        engine,
    )

    rows = df.to_dict(orient="records")

    with engine.begin() as connection:
        connection.execute(text("TRUNCATE mart.valuation_summary"))
        if rows:
            connection.execute(
                text("""
                    INSERT INTO mart.valuation_summary (
                        "Ticker", "Nom", "Cours", "PE", "PS", "EPS", "SPS",
                        "dividend_yield", "as_of_date"
                    )
                    VALUES (
                        :Ticker, :Nom, :Cours, :PE, :PS, :EPS, :SPS,
                        :dividend_yield, :as_of_date
                    )
                    """),
                rows,
            )
