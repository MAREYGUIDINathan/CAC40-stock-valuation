CREATE TABLE IF NOT EXISTS raw.market_prices (
    "Date" DATE NOT NULL,
    "Open" DOUBLE PRECISION,
    "High" DOUBLE PRECISION,
    "Low" DOUBLE PRECISION,
    "Close" DOUBLE PRECISION,
    "Volume" BIGINT,
    "Ticker" TEXT NOT NULL,
    PRIMARY KEY ("Date", "Ticker")
);

CREATE TABLE IF NOT EXISTS raw.balance_sheet (
    "Date" DATE NOT NULL,
    "Ticker" TEXT NOT NULL,
    "OrdinarySharesNumber" DOUBLE PRECISION,
    "TotalDebt" DOUBLE PRECISION,
    "CommonStockEquity" DOUBLE PRECISION,
    "CashAndCashEquivalents" DOUBLE PRECISION,
    PRIMARY KEY ("Date", "Ticker")
);

CREATE TABLE IF NOT EXISTS raw.financials (
    "Date" DATE NOT NULL,
    "Ticker" TEXT NOT NULL,
    "NetIncome" DOUBLE PRECISION,
    "TotalRevenue" DOUBLE PRECISION,
    "OperatingIncome" DOUBLE PRECISION,
    PRIMARY KEY ("Date", "Ticker")
);

CREATE TABLE IF NOT EXISTS raw.cac40 (
    "Nom" TEXT NOT NULL,
    "Ticker" TEXT NOT NULL,
    PRIMARY KEY ("Ticker")
);

CREATE TABLE IF NOT EXISTS raw.dividends (
    "Date" DATE NOT NULL,
    "Ticker" TEXT NOT NULL,
    "Amount" DOUBLE PRECISION NOT NULL,
    PRIMARY KEY ("Date", "Ticker")
);

CREATE TABLE IF NOT EXISTS mart.pe_ps_ratios (
    "Date" DATE NOT NULL,
    "Ticker" TEXT NOT NULL,
    "PE" DOUBLE PRECISION,
    "PS" DOUBLE PRECISION,
    "sps" DOUBLE PRECISION,
    "eps" DOUBLE PRECISION,
    "dividend_yield" DOUBLE PRECISION,
    PRIMARY KEY ("Date", "Ticker")
);

