# ANIVERSE — Anime Discovery & Recommendation System

A Netflix-inspired Streamlit anime discovery app powered by the AniList GraphQL API. It no longer depends on Jikan.

## Features
- Home page with an automatically advancing featured-anime slider (every five seconds), plus manual Previous/Next controls.
- Trending, top-rated, current-season releases, title search, anime details, and recommendations.
- Responsive black-and-crimson UI with poster cards and a recommendation engine.
- Short network timeout, five-minute successful-data cache, and visible retry controls for failed requests.

## Run on Windows / PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL Streamlit prints in the terminal (normally `http://localhost:8501`). Internet access is required for live AniList data and poster images.

## API note
The app queries `https://graphql.anilist.co`. If it cannot be reached from your network, check DNS/firewall/VPN settings. A third-party API cannot be guaranteed to be reachable from every network.

## Analytics dashboard
- Open **📊 Analytics Dashboard** from the sidebar.
- On first visit, the dashboard collects up to 200 anime records from AniList and saves a local snapshot to `data/anime_dataset.csv`.
- Use **Refresh API data** to collect a fresh snapshot when the API is reachable.
- Explore average scores, genre counts and scores, release-year groups, score-vs-popularity patterns, and the filtered records table.
- Download the currently filtered records as CSV.
- The dashboard uses Pandas for cleaning/analysis and Plotly for interactive charts. The CSV is generated from API responses; it is not a hand-made or bundled dataset.

If AniList is temporarily unavailable, the dashboard uses the saved CSV snapshot when one has already been created. On a first run with no connection and no saved CSV, there will be no data to analyze until the API can be reached.
