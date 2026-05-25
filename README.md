# CAC40 Stock Valuation

(Version française plus bas)

[Live Demo](https://streamlit.nathan-mg.com)

## Introduction

End-to-end Data Engineering pipeline that tracks and visualizes stock valuation ratios (P/E, P/S, Dividend Yield) for all 40 companies of the CAC40 index, updated daily.

👉 [View the live dashboard](https://streamlit.nathan-mg.com)

The subject of stock valuation was chosen because understanding how stocks are priced is genuinely useful — and comparing a stock's price against a company's fundamentals is the foundation of any serious analysis.

**Tech stack:** Docker Compose · Apache Airflow · PostgreSQL · FastAPI · Streamlit

Everything is open-source, designed to deliver an end-to-end data project at low cost.

## Features

- **Fully autonomous data pipeline** (updated every day)
  - List of companies included in the CAC40
  - Balance sheet and financials for all companies
  - Latest stock market price (day n-1)
  - Day-by-day ratio calculation (Price-to-Earnings, Price-to-Sales, Dividend Yield)
- **Dashboard**
  - Select one or more CAC40 companies, a period (1 month, 6 months, current year, 1 year, 5 years), and a ratio to compare
  - Explanation of each ratio used
  - Cards showing the latest stock valuation for selected companies and variation over the selected period
  - Line chart showing stock valuation evolution over the selected period
  - Line chart showing selected ratio evolution over the selected period
  - Bar chart ranking companies by their latest calculated ratio
  - Summary table showing all latest values for all selected companies

## Architecture

![Project architecture](image.png)

The pipeline runs daily via Airflow. CAC40 companies list is scrapped from the Euronext website, Raw financial (stock prices, balance sheet & financials) data is fetched from an external API, stored in PostgreSQL, served through a FastAPI layer, and visualized in Streamlit. Everything runs in Docker Compose.

FastAPI acts as a security layer between Streamlit and the database — credentials are never exposed to the frontend. It also makes the data reusable by any other client (mobile app, third-party integration, etc.) without touching the database layer.

## Run locally

```bash
git clone https://github.com/MAREYGUIDINathan/CAC40-stock-valuation.git
cd cac40-stock-valuation
```

rename ".env.exemple" to ".env" then change credentials

```bash
docker compose up
```

once every container is up got to http://127.0.0.1:8080/ and connect with username airflow and the credentials you put in the .env  
after that go to dag and launch cac40_valuation  
then you can visit the dashboard (http://127.0.0.1:8501/)

## Known issues

- ArcelorMittal data not showing due to an issue with the API used — needs either an exception handler or a pipeline fix

---







(English version on top)

## Introduction

Pipeline de Data Engineering de bout en bout qui suit et visualise les ratios de valorisation boursière (PER, P/CA, Rendement du dividende) pour les 40 entreprises du CAC40, mis à jour quotidiennement.

👉 [Voir le dashboard en production](https://streamlit.nathan-mg.com)

Le sujet de la valorisation boursière a été choisi parce que comprendre comment les actions sont valorisées est genuinement utile — et comparer le prix d'une action aux fondamentaux de l'entreprise est la base de toute analyse sérieuse.

**Stack technique :** Docker Compose · Apache Airflow · PostgreSQL · FastAPI · Streamlit

Tout est open-source et auto-hébergé, conçu pour livrer un projet data complet à faible coût.

## Fonctionnalités

- **Pipeline de données entièrement autonome** (mis à jour chaque jour)
  - Liste des entreprises incluses dans le CAC40
  - Bilan et données financières de toutes les entreprises
  - Dernier cours boursier (jour n-1)
  - Calcul quotidien des ratios (PER, Price-to-Sales, Rendement du dividende)
- **Dashboard**
  - Sélectionner une ou plusieurs entreprises du CAC40, une période (1 mois, 6 mois, année en cours, 1 an, 5 ans) et un ratio à comparer
  - Explication de chaque ratio utilisé
  - Cartes affichant la dernière valorisation et la variation sur la période sélectionnée
  - Graphique linéaire de l'évolution du cours boursier sur la période
  - Graphique linéaire de l'évolution du ratio sélectionné sur la période
  - Graphique en barres classant les entreprises par leur dernier ratio calculé
  - Tableau récapitulatif des dernières valeurs pour toutes les entreprises sélectionnées

## Architecture

![Schéma du projet](image.png)

Le pipeline tourne quotidiennement via Airflow. La liste des entreprises du CAC40 est scrappé sur le site Euronext et les données financières (cours de l'action et résultats/bilan financiers) sont récupérées en utilisant l'API Yfinnance, stockées dans PostgreSQL, distribuées via une couche FastAPI, et visualisées dans Streamlit. Tout tourne dans un Docker Compose.

FastAPI joue le rôle de couche de sécurité entre Streamlit et la base de données, les mots de passe ne sont jamais exposés côté front. Cela permet également de réutiliser les données depuis n'importe quel autre client (application mobile, intégration tierce, etc.) sans toucher à la couche base de données.

## Lancer en local

```bash
git clone https://github.com/MAREYGUIDINathan/CAC40-stock-valuation.git
cd cac40-stock-valuation
```

renommer ".env.exemple" en ".env" et changer les mots de passe

```bash
docker compose up
```

Une fois que tous les conteneurs sont lancés, allez sur http://127.0.0.1:8080/ et connectez-vous à Airflow en utilisant le nom d'utilisateur "airflow" et le mdp que vous avez rempli dans le .env  
une fois connecté, cliquer sur l'onglet "dag" et lancer le dag cac40_valuation  
maintenant vous pouvez visiter le dashboard (http://127.0.0.1:8501/)

## Bugs connus

- Les données d'ArcelorMittal ne s'affichent pas en raison d'un problème avec l'API utilisée — nécessite soit un gestionnaire d'exception soit une correction du pipeline

