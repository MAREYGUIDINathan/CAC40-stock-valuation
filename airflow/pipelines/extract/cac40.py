import os
import time

from db.connection import _postgres_connection_url
from sqlalchemy import create_engine, text
import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def load_cac40() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://live.euronext.com/en/popout-page/getIndexComposition/FR0003500008-XPAR")
        
        # Attend que le tableau soit présent
        page.wait_for_selector("#AwlIndexCompositionTableCanvas tbody tr")
        
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "AwlIndexCompositionTableCanvas"})

    lignes = table.find_all("tr")[1:]
    données = []
    for ligne in lignes:
        cellules = ligne.find_all("td")
        données.append({
            "nom": cellules[0].get_text(strip=True),
            "isin": cellules[1].get_text(strip=True),
            "bourse": cellules[2].get_text(strip=True),
            "pays": cellules[3].get_text(strip=True),
        })

    df = pd.DataFrame(données)

    def isins_to_tickers(isins, exch_code="FP"):
        """Map ISINs to Yahoo-style tickers via OpenFIGI (batched to avoid rate limits)."""
        api_key = os.environ.get("OPENFIGI_API_KEY")
        batch_size = 100 if api_key else 10  # no key: max 10 jobs/request, ~25 requests/min

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-OPENFIGI-APIKEY"] = api_key

        tickers = {}
        for offset in range(0, len(isins), batch_size):
            chunk = list(isins[offset : offset + batch_size])
            jobs = [
                {"idType": "ID_ISIN", "idValue": isin, "exchCode": exch_code}
                for isin in chunk
            ]

            for attempt in range(5):
                response = requests.post(
                    "https://api.openfigi.com/v3/mapping",
                    json=jobs,
                    headers=headers,
                    timeout=30,
                )
                if response.status_code == 429:
                    time.sleep(2**attempt + 2)
                    continue
                break
            else:
                raise RuntimeError("OpenFIGI rate limit exceeded; retry in a minute.")

            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenFIGI HTTP {response.status_code}: {response.text[:200]}"
                )

            for isin, item in zip(chunk, response.json()):
                tickers[isin] = item["data"][0]["ticker"] if item.get("data") else None

            if offset + batch_size < len(isins):
                time.sleep(2.5)  # stay under 25 req/min without an API key

        return tickers


    ticker_map = isins_to_tickers(df["isin"].tolist())
    df["ticker"] = df["isin"].map(ticker_map)
    df["yahoo"] = df["ticker"].apply(lambda t: f"{t}.PA" if t else None)

    rows = df.to_dict(orient="records")

    if rows:
        engine = create_engine(_postgres_connection_url())
        with engine.begin() as connection:
            # Clear the table before inserting the new values
            connection.execute(text('TRUNCATE TABLE raw.cac40'))
            connection.execute(
                text("""
                    INSERT INTO raw.cac40 ("Nom", "Ticker")
                    VALUES (:nom, :yahoo)
                    """),
                rows,
            )