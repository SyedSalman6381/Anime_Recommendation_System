"""AniList GraphQL API helpers and shared ANIVERSE UI utilities.

Uses AniList IDs and a normalized anime shape so all existing pages and the
recommendation engine can consume the same fields.
"""
from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

API_URL = "https://graphql.anilist.co"
REQUEST_TIMEOUT = 9
CACHE_TTL = 300
RECOMMENDATION_CACHE_TTL = 600
MAX_RESULTS = 25

FIELDS = """
id idMal
idMal
siteUrl
isAdult
format
status
episodes
season
seasonYear
duration
averageScore
popularity
favourites
description
startDate { year }
title { romaji english native }
coverImage { extraLarge large medium }
bannerImage
genres
tags { name }
studios(isMain: true) { nodes { name } }
""".replace("id idMal\nidMal", "id\nidMal")


def _graphql(query: str, variables: Optional[dict] = None) -> Optional[dict]:
    """Make one bounded GraphQL request; fail quickly with a useful empty state."""
    try:
        response = requests.post(
            API_URL,
            json={"query": query, "variables": variables or {}},
            headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "ANIVERSE anime discovery app"},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 429:
            return None
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            return None
        return payload.get("data")
    except (requests.RequestException, ValueError, TypeError):
        return None


def _query_media(sort: str, limit: int = MAX_RESULTS, search: str = "", anime_id: Optional[int] = None,
                 season: str = "", season_year: Optional[int] = None, genres: Optional[List[str]] = None, page: int = 1) -> List[dict]:
    query = f"""
    query ($page: Int, $perPage: Int, $search: String, $id: Int, $season: MediaSeason,
           $seasonYear: Int, $genres: [String]) {{
      Page(page: $page, perPage: $perPage) {{
        media(type: ANIME, sort: {sort}, search: $search, id: $id, season: $season,
              seasonYear: $seasonYear, genre_in: $genres, isAdult: false) {{
          {FIELDS}
        }}
      }}
    }}
    """
    variables: Dict[str, Any] = {"page": max(1, int(page)), "perPage": max(1, min(int(limit), 50))}
    if search:
        variables["search"] = search
    if anime_id is not None:
        variables["id"] = int(anime_id)
    if season:
        variables["season"] = season
    if season_year:
        variables["seasonYear"] = int(season_year)
    if genres:
        variables["genres"] = genres
    data = _graphql(query, variables)
    media = ((data or {}).get("Page") or {}).get("media") or []
    return [normalize_anilist(x) for x in media if isinstance(x, dict)]


def normalize_anilist(item: Dict[str, Any]) -> Dict[str, Any]:
    title = item.get("title") or {}
    cover = item.get("coverImage") or {}
    start_date = item.get("startDate") or {}
    score = item.get("averageScore") or 0
    studios = ((item.get("studios") or {}).get("nodes") or [])
    tags = item.get("tags") or []
    return {
        "id": item.get("id"),
        "idMal": item.get("idMal"),
        "title": {"english": title.get("english") or "", "romaji": title.get("romaji") or "", "native": title.get("native") or ""},
        "description": item.get("description") or "",
        "episodes": item.get("episodes") or 0,
        "duration": f"{item['duration']} min" if item.get("duration") else "Unknown",
        "status": (item.get("status") or "Unknown").replace("_", " ").title(),
        "season": (item.get("season") or "").title(),
        "seasonYear": item.get("seasonYear") or start_date.get("year") or "",
        "averageScore": score,
        "score": score,
        "popularity": item.get("popularity") or 0,
        "members": item.get("popularity") or 0,
        "genres": item.get("genres") or [],
        "tags": tags,
        "studios": {"nodes": studios},
        "coverImage": {"extraLarge": cover.get("extraLarge") or cover.get("large") or cover.get("medium") or "", "large": cover.get("large") or "", "medium": cover.get("medium") or ""},
        "bannerImage": item.get("bannerImage") or cover.get("extraLarge") or cover.get("large") or "",
        "siteUrl": item.get("siteUrl") or (f"https://myanimelist.net/anime/{item['idMal']}" if item.get("idMal") else "https://anilist.co/anime/" + str(item.get("id", ""))),
        "type": item.get("format") or "TV",
        "format": item.get("format") or "TV",
        "source": "AniList",
        "aired": {},
        "trailer": {},
        "favourites": item.get("favourites") or 0,
    }


def title_of(anime: Dict[str, Any]) -> str:
    title = anime.get("title") or {}
    if isinstance(title, str):
        return title or "Unknown Anime"
    return title.get("english") or title.get("romaji") or title.get("native") or "Unknown Anime"


def poster_of(anime: Dict[str, Any]) -> str:
    cover = anime.get("coverImage") or {}
    return cover.get("extraLarge") or cover.get("large") or cover.get("medium") or ""


def banner_of(anime: Dict[str, Any]) -> str:
    return anime.get("bannerImage") or poster_of(anime)


def genres_of(anime: Dict[str, Any]) -> List[str]:
    return [x if isinstance(x, str) else x.get("name", "") for x in (anime.get("genres") or []) if (x if isinstance(x, str) else x.get("name"))]


def studios_of(anime: Dict[str, Any]) -> List[str]:
    studios = anime.get("studios") or {}
    values = studios.get("nodes") or [] if isinstance(studios, dict) else studios
    return [x if isinstance(x, str) else x.get("name", "") for x in values if (x if isinstance(x, str) else x.get("name"))]


def score_of(anime: Dict[str, Any]) -> float:
    try:
        value = float(anime.get("averageScore", anime.get("score", 0)) or 0)
        return value / 10 if value > 10 else value
    except (TypeError, ValueError):
        return 0.0


def year_of(anime: Dict[str, Any]) -> str:
    return str(anime.get("seasonYear") or (anime.get("startDate") or {}).get("year") or "N/A")


def clean_description(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip() or "No synopsis available."


def format_number(value: Any) -> str:
    try:
        number = int(value)
        return f"{number:,}" if number else "N/A"
    except (TypeError, ValueError):
        return "N/A"


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_top_anime(limit: int = MAX_RESULTS) -> List[Dict[str, Any]]:
    return _query_media("SCORE_DESC", limit)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_current_season(limit: int = MAX_RESULTS) -> List[Dict[str, Any]]:
    now = datetime.now()
    season = "WINTER" if now.month in (12, 1, 2) else "SPRING" if now.month in (3, 4, 5) else "SUMMER" if now.month in (6, 7, 8) else "FALL"
    year = now.year + (1 if now.month == 12 else 0)
    return _query_media("POPULARITY_DESC", limit, season=season, season_year=year)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_trending(limit: int = MAX_RESULTS) -> List[Dict[str, Any]]:
    return _query_media("TRENDING_DESC", limit)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def search_anime(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    query = query.strip()
    return _query_media("SEARCH_MATCH", limit, search=query) if query else []


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_anime_details(anime_id: int) -> Optional[Dict[str, Any]]:
    results = _query_media("POPULARITY_DESC", 1, anime_id=int(anime_id))
    return results[0] if results else None


@st.cache_data(ttl=RECOMMENDATION_CACHE_TTL, show_spinner=False)
def get_jikan_recommendations(anime_id: int) -> List[Dict[str, Any]]:
    # Kept as a compatibility function for the existing recommender interface.
    return []


@st.cache_data(ttl=RECOMMENDATION_CACHE_TTL, show_spinner=False)
def build_recommendation_pool(selected_id: int) -> List[Dict[str, Any]]:
    selected = get_anime_details(selected_id)
    if not selected:
        return []
    pool = get_top_anime(25) + get_current_season(25) + get_trending(25)
    for genre in genres_of(selected)[:2]:
        pool.extend(_query_media("POPULARITY_DESC", 12, genres=[genre]))
    result, seen = [], {int(selected_id)}
    for anime in pool:
        aid = anime.get("id")
        if not aid or aid in seen:
            continue
        result.append(anime)
        seen.add(aid)
    return result[:100]


@st.cache_data(ttl=1800, show_spinner=False)
def get_analytics_catalogue(pages: int = 4, per_page: int = 50) -> List[Dict[str, Any]]:
    """Fetch a paginated catalogue snapshot for analytics (up to 200 titles by default)."""
    records: List[Dict[str, Any]] = []
    seen = set()
    for page_number in range(1, max(1, min(int(pages), 10)) + 1):
        batch = _query_media("POPULARITY_DESC", per_page, page=page_number)
        if not batch:
            break
        for anime in batch:
            anime_id = anime.get("id")
            if anime_id and anime_id not in seen:
                records.append(anime)
                seen.add(anime_id)
    return records


def current_season() -> str:
    month = datetime.now().month
    return {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer", 9: "Fall", 10: "Fall", 11: "Fall"}[month]


def setup(page_title: str, page_icon: str = "🎌"):
    root = Path(__file__).resolve().parent
    st.set_page_config(page_title=f"ANIVERSE | {page_title}", page_icon=page_icon, layout="wide", initial_sidebar_state="expanded")
    css_path = root / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-icon">🎌</div><div class="brand-name"><span>ANI</span>VERSE</div></div><div class="side-copy">Discover anime, explore hidden gems, and get intelligent recommendations.</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-heading">EXPLORE</div>', unsafe_allow_html=True)
        st.page_link("app.py", label="⌂  Home")
        st.page_link("pages/01_Trending.py", label="🔥  Trending")
        st.page_link("pages/02_Top_Rated.py", label="⭐  Top Rated")
        st.page_link("pages/03_New_Releases.py", label="🆕  New Releases")
        st.page_link("pages/04_Search.py", label="🔎  Search")
        st.page_link("pages/06_Recommendations.py", label="🤖  Recommendations")
        st.page_link("pages/07_Analytics_Dashboard.py", label="📊  Analytics Dashboard")
        st.divider()
        st.caption("LIVE CATALOGUE · ANILIST")
    st.markdown(f'<div class="app-header"><div><span class="header-brand">ANIVERSE</span><span class="header-divider">/</span><span class="header-page">{html.escape(page_title)}</span></div><div class="header-status"><span class="status-dot"></span> LIVE · ANILIST</div></div>', unsafe_allow_html=True)


def card(anime, key, match=None, reasons=None):
    title = title_of(anime); image = poster_of(anime); score = score_of(anime)
    genres = ''.join(f'<span class="genre">{html.escape(g)}</span>' for g in genres_of(anime)[:3])
    image_html = f'<img class="poster" src="{html.escape(image)}" alt="{html.escape(title)}" loading="lazy">' if image else '<div class="poster"></div>'
    match_html = f'<span class="match">✦ {round(match*100)}% match</span>' if match is not None else ''
    st.markdown(f'<div class="card">{image_html}<div class="card-body"><div class="card-title">{html.escape(title)}</div><div class="card-meta">{html.escape(year_of(anime))} · {html.escape(str(anime.get("type", "TV")))} · {html.escape(str(anime.get("episodes") or "N/A"))} eps</div><div class="card-score">★ {score:.1f}/10</div><div>{genres}</div>{match_html}</div></div>', unsafe_allow_html=True)
    if reasons:
        st.caption(" · ".join(reasons[:2]))
    return st.button("View details", key=f"details_{key}", use_container_width=True)


def grid(items, prefix="anime", matches=None):
    if not items:
        st.warning("Anime could not be loaded from AniList. Check your internet connection and try again.")
        if st.button("Retry loading", key=f"retry_{prefix}"):
            st.cache_data.clear()
            st.rerun()
        return
    for start in range(0, len(items), 5):
        cols = st.columns(5, gap="medium")
        for offset, anime in enumerate(items[start:start+5]):
            i = start + offset
            with cols[offset]:
                match = matches[i]["score"] if matches and i < len(matches) else None
                reasons = matches[i]["reasons"] if matches and i < len(matches) else None
                if card(anime, f"{prefix}_{i}_{anime.get('id')}", match, reasons):
                    st.session_state["selected_anime_id"] = anime.get("id")
                    st.switch_page("pages/05_Anime_Details.py")
