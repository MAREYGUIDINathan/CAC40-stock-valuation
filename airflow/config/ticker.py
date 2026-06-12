from sqlalchemy import create_engine, text

from db.connection import _postgres_connection_url


def get_cac40_tickers() -> list[str]:
    engine = create_engine(_postgres_connection_url())
    with engine.connect() as connection:
        result = connection.execute(
            text('SELECT "Ticker" FROM raw.cac40 WHERE "Ticker" IS NOT NULL ORDER BY "Ticker"')
        )
        tickers = [row[0] for row in result]
    if not tickers:
        raise ValueError("raw.cac40 is empty; run load_cac40 first.")
    return tickers
