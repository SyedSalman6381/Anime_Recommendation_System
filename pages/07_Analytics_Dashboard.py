"""ANIVERSE Analytics Dashboard — analysis of live AniList API catalogue snapshots."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from api import get_analytics_catalogue, get_top_anime, get_trending, get_current_season, setup, title_of, genres_of, score_of, year_of

setup("Analytics Dashboard", "📊")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "anime_dataset.csv"

st.markdown("""
<style>
.analytics-hero{padding:1.4rem 1.5rem;border:1px solid #38202a;border-radius:18px;background:linear-gradient(120deg,rgba(120,15,42,.38),rgba(18,18,23,.96));margin:.5rem 0 1.25rem}
.analytics-kicker{color:#ff647e;font-size:.72rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase}
.analytics-hero h1{margin:.3rem 0 .35rem;font-size:2.1rem;font-weight:850;color:#fff}
.analytics-hero p{margin:0;color:#c8c4cb;max-width:850px}
.metric-card{background:linear-gradient(145deg,#1c1b21,#111115);border:1px solid #34252c;border-radius:14px;padding:1rem 1.1rem;min-height:105px}
.metric-label{color:#bcb6bf;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700}
.metric-value{font-size:1.8rem;font-weight:850;color:#fff;margin-top:.3rem}
.metric-note{font-size:.75rem;color:#ff7b91;margin-top:.15rem}
.insight{border-left:3px solid #e11d48;background:#1b171d;padding:.75rem .9rem;border-radius:0 9px 9px 0;margin:.4rem 0;color:#e7e1e8}
</style>
<div class="analytics-hero">
  <div class="analytics-kicker">ANIVERSE · DATA INTELLIGENCE</div>
  <h1>Anime Analytics Dashboard</h1>
  <p>Explore ratings, genres, release patterns and popularity using structured snapshots collected from the AniList API.</p>
</div>
""", unsafe_allow_html=True)


def records_to_frame(records: list[dict]) -> pd.DataFrame:
    rows = []
    for anime in records:
        if not isinstance(anime, dict):
            continue
        try:
            year = int(year_of(anime))
        except (TypeError, ValueError):
            year = None
        rows.append({
            "id": anime.get("id"),
            "title": title_of(anime),
            "score": round(float(score_of(anime) or 0), 2),
            "popularity": int(anime.get("popularity") or anime.get("members") or 0),
            "favourites": int(anime.get("favourites") or 0),
            "genres": ", ".join(genres_of(anime)),
            "episodes": int(anime.get("episodes") or 0),
            "year": year,
            "format": str(anime.get("format") or anime.get("type") or "Unknown"),
            "status": str(anime.get("status") or "Unknown"),
            "season": str(anime.get("season") or "Unknown"),
            "url": str(anime.get("siteUrl") or ""),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates(subset=["id"], keep="first")
    df = df[df["title"].notna() & (df["title"].astype(str).str.strip() != "")]
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce").fillna(0)
    df["favourites"] = pd.to_numeric(df["favourites"], errors="coerce").fillna(0)
    df["episodes"] = pd.to_numeric(df["episodes"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    return df


def read_saved_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(CSV_PATH)
        if not df.empty and "id" in df.columns:
            df = df.drop_duplicates(subset=["id"])
            for col in ["score", "popularity", "favourites", "episodes", "year"]:
                if col in df:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
    except (OSError, ValueError, pd.errors.ParserError):
        return pd.DataFrame()
    return pd.DataFrame()


def save_data(df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")


# Refresh is an explicit user action, so normal page navigation doesn't repeatedly hit the API.
left, right = st.columns([3, 1], vertical_alignment="center")
with left:
    st.caption("Data source: AniList GraphQL API · Public anime metadata · Non-adult catalogue")
with right:
    refresh = st.button("↻ Refresh API data", type="primary", use_container_width=True)

if refresh:
    with st.spinner("Collecting anime records from AniList…"):
        st.cache_data.clear()
        live_records = get_analytics_catalogue(pages=4, per_page=50)
        fresh_df = records_to_frame(live_records)
        if not fresh_df.empty:
            save_data(fresh_df)
            st.session_state["analytics_data_source"] = "fresh"
            st.success(f"Updated snapshot with {len(fresh_df):,} unique anime records.")
        else:
            st.warning("AniList did not return data this time. The saved dataset, if available, will be used.")

# First visit: collect a catalogue once, then persist a snapshot so analytics works during API downtime.
df = read_saved_data()
if df.empty:
    with st.spinner("Loading the first anime dataset from AniList…"):
        live_records = get_analytics_catalogue(pages=4, per_page=50)
        if not live_records:
            # Graceful fallback to existing app API calls if pagination is temporarily unavailable.
            live_records = get_top_anime(50) + get_trending(50) + get_current_season(50)
        df = records_to_frame(live_records)
        if not df.empty:
            save_data(df)
            st.session_state["analytics_data_source"] = "fresh"

if df.empty:
    st.error("No anime data is available yet. Check your internet connection and select Refresh API data to try again.")
    st.stop()

source_note = "Saved API snapshot" if CSV_PATH.exists() else "Current API response"
try:
    modified = datetime.fromtimestamp(CSV_PATH.stat().st_mtime).strftime("%d %b %Y, %I:%M %p") if CSV_PATH.exists() else "not saved"
except OSError:
    modified = "unknown"
st.caption(f"{source_note} · Last snapshot saved: {modified} · {len(df):,} unique records")

# Sidebar-like filters on the dashboard itself.
st.markdown("### Filter the catalogue")
filter_cols = st.columns([1.25, 1.25, 1.25, 1.4])
all_genres = sorted({g.strip() for value in df.get("genres", pd.Series(dtype=str)).dropna() for g in str(value).split(",") if g.strip()})
with filter_cols[0]:
    selected_genres = st.multiselect("Genres", all_genres, placeholder="All genres")
with filter_cols[1]:
    formats = sorted(df["format"].dropna().astype(str).unique().tolist()) if "format" in df else []
    selected_formats = st.multiselect("Format", formats, placeholder="All formats")
with filter_cols[2]:
    years = pd.to_numeric(df.get("year", pd.Series(dtype=float)), errors="coerce").dropna()
    if not years.empty:
        year_min, year_max = int(years.min()), int(years.max())
        year_range = st.slider("Release year", min_value=year_min, max_value=max(year_min, year_max), value=(year_min, max(year_min, year_max)))
    else:
        year_range = None
with filter_cols[3]:
    valid_scores = pd.to_numeric(df.get("score", pd.Series(dtype=float)), errors="coerce").dropna()
    score_max = max(10.0, float(valid_scores.max())) if not valid_scores.empty else 10.0
    score_range = st.slider("Score range", min_value=0.0, max_value=10.0, value=(0.0, 10.0), step=0.5)

filtered = df.copy()
if selected_genres:
    filtered = filtered[filtered["genres"].fillna("").apply(lambda x: any(g in [v.strip() for v in str(x).split(",")] for g in selected_genres))]
if selected_formats:
    filtered = filtered[filtered["format"].astype(str).isin(selected_formats)]
if year_range and "year" in filtered:
    filtered = filtered[filtered["year"].isna() | filtered["year"].between(year_range[0], year_range[1])]
if "score" in filtered:
    # Keep unrated titles in the table when score is set to its full range.
    filtered = filtered[filtered["score"].between(score_range[0], score_range[1]) | filtered["score"].isna()]

if filtered.empty:
    st.warning("No anime match those filters. Widen the year or score range, or clear a genre/format selection.")
    st.stop()

# KPI row
scored = filtered[filtered["score"].fillna(0) > 0]
top_anime = scored.sort_values("score", ascending=False).head(1)
top_title = str(top_anime.iloc[0]["title"]) if not top_anime.empty else "N/A"
top_score = float(top_anime.iloc[0]["score"]) if not top_anime.empty else 0
avg_score = float(scored["score"].mean()) if not scored.empty else 0
avg_pop = float(filtered["popularity"].mean()) if "popularity" in filtered else 0
kpis = st.columns(4, gap="medium")
metrics = [
    ("ANIME ANALYZED", f"{len(filtered):,}", "Unique API records after filters"),
    ("AVERAGE SCORE", f"{avg_score:.2f}/10" if avg_score else "N/A", "Community score converted to 10-point scale"),
    ("TOP RATED IN VIEW", f"{top_score:.1f}/10" if top_score else "N/A", top_title[:34]),
    ("AVG. POPULARITY", f"{avg_pop:,.0f}", "AniList popularity metric"),
]
for col, (label, value, note) in zip(kpis, metrics):
    with col:
        st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)

st.markdown("### Explore the data")
chart_left, chart_right = st.columns(2, gap="large")
plot_df = filtered.copy()
plot_df["genres_list"] = plot_df["genres"].fillna("").apply(lambda x: [g.strip() for g in str(x).split(",") if g.strip()])
exploded = plot_df.explode("genres_list")
exploded = exploded[exploded["genres_list"].notna() & (exploded["genres_list"] != "")]
with chart_left:
    st.markdown("#### Most represented genres")
    genre_counts = exploded["genres_list"].value_counts().head(12).rename_axis("Genre").reset_index(name="Anime count")
    if not genre_counts.empty:
        fig = px.bar(genre_counts.sort_values("Anime count"), x="Anime count", y="Genre", orientation="h", color="Anime count", color_continuous_scale=[[0,"#65152c"],[1,"#ff355e"]], template="plotly_dark")
        fig.update_layout(height=400, margin=dict(l=5,r=5,t=15,b=5), coloraxis_showscale=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Genre information is not available for the selected records.")
with chart_right:
    st.markdown("#### Average score by genre")
    genre_scores = exploded[exploded["score"].fillna(0) > 0].groupby("genres_list", as_index=False).agg(avg_score=("score", "mean"), titles=("id", "nunique"))
    genre_scores = genre_scores[genre_scores["titles"] >= 2].sort_values("avg_score", ascending=False).head(12)
    if not genre_scores.empty:
        fig = px.bar(genre_scores.sort_values("avg_score"), x="avg_score", y="genres_list", orientation="h", hover_data=["titles"], color="avg_score", range_color=(0,10), color_continuous_scale=[[0,"#65152c"],[1,"#ff355e"]], template="plotly_dark", labels={"avg_score":"Average score","genres_list":"Genre","titles":"Anime count"})
        fig.update_layout(height=400, margin=dict(l=5,r=5,t=15,b=5), coloraxis_showscale=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(range=[0,10])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("At least two scored titles per genre are needed for this chart.")

chart_left, chart_right = st.columns(2, gap="large")
with chart_left:
    st.markdown("#### Anime release trend")
    trend = filtered.dropna(subset=["year"]).groupby("year", as_index=False).agg(anime_count=("id", "nunique"))
    if not trend.empty:
        trend["year"] = trend["year"].astype(int).astype(str)
        fig = px.line(trend.sort_values("year"), x="year", y="anime_count", markers=True, template="plotly_dark", labels={"year":"Release year","anime_count":"Anime in API snapshot"})
        fig.update_traces(line=dict(color="#ff355e", width=3), marker=dict(size=7, color="#ff7891"))
        fig.update_layout(height=350, margin=dict(l=5,r=5,t=15,b=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Release-year information is not available.")
with chart_right:
    st.markdown("#### Score vs. popularity")
    scatter = filtered[(filtered["score"].fillna(0) > 0) & (filtered["popularity"].fillna(0) > 0)].copy()
    if len(scatter) >= 2:
        fig = px.scatter(scatter, x="popularity", y="score", hover_name="title", hover_data={"year":True,"genres":True,"popularity":":,"}, color="score", color_continuous_scale=[[0,"#8c1937"],[1,"#ff6b86"]], template="plotly_dark", labels={"popularity":"AniList popularity","score":"Average score (0–10)"})
        fig.update_layout(height=350, margin=dict(l=5,r=5,t=15,b=5), coloraxis_showscale=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        corr_df = scatter[["score", "popularity"]].corr(numeric_only=True)
        corr = corr_df.loc["score", "popularity"]
        if pd.notna(corr):
            direction = "positive" if corr > 0.15 else "negative" if corr < -0.15 else "weak or near zero"
            st.caption(f"Pearson correlation in the filtered snapshot: {corr:.2f} ({direction} linear relationship). Correlation does not imply causation.")
    else:
        st.info("At least two rated, popularity-ranked anime are needed for this chart.")

st.markdown("### Data insights")
if not exploded.empty:
    common_genre = exploded["genres_list"].value_counts().index[0]
    st.markdown(f'<div class="insight"><b>Most represented genre:</b> {common_genre} in the current filtered catalogue.</div>', unsafe_allow_html=True)
if not trend.empty:
    trend_counts = trend.copy()
    trend_counts["year_num"] = pd.to_numeric(trend_counts["year"], errors="coerce")
    latest_year_row = trend_counts.sort_values("anime_count", ascending=False).head(1)
    if not latest_year_row.empty:
        st.markdown(f'<div class="insight"><b>Largest release-year group in this snapshot:</b> {latest_year_row.iloc[0]["year"]} ({int(latest_year_row.iloc[0]["anime_count"])} titles). This describes the collected API sample, not necessarily all anime released that year.</div>', unsafe_allow_html=True)
if not top_anime.empty:
    st.markdown(f'<div class="insight"><b>Highest-rated title in the current view:</b> {top_title} ({top_score:.1f}/10).</div>', unsafe_allow_html=True)

st.markdown("### Anime records")
search_text = st.text_input("Find a title in this table", placeholder="Type an anime title…")
table = filtered.copy()
if search_text.strip():
    table = table[table["title"].astype(str).str.contains(search_text.strip(), case=False, na=False)]
show_cols = [c for c in ["title", "score", "popularity", "favourites", "genres", "year", "format", "episodes", "status"] if c in table.columns]
st.dataframe(table[show_cols].sort_values("score", ascending=False, na_position="last"), use_container_width=True, hide_index=True, height=380)
csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button("⬇ Download filtered analysis (CSV)", data=csv_bytes, file_name="aniverse_filtered_analysis.csv", mime="text/csv")

st.markdown("---")
st.caption("Methodology: records are fetched from AniList's public GraphQL API, deduplicated by AniList ID, normalized into a Pandas DataFrame and saved as a CSV snapshot. Scores are community ratings; popularity is AniList's popularity metric, not a verified viewer count. Charts describe the collected sample and may change when the snapshot is refreshed.")
