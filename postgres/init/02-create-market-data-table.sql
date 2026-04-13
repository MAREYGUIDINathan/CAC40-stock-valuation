CREATE TABLE IF NOT EXISTS market_data.daily_prices (
    "Date" DATE NOT NULL,
    "Open" DOUBLE PRECISION,
    "High" DOUBLE PRECISION,
    "Low" DOUBLE PRECISION,
    "Close" DOUBLE PRECISION,
    "Volume" BIGINT,
    "Ticker" TEXT NOT NULL,
    PRIMARY KEY ("Date", "Ticker")
);