"""ANIVERSE home page with a reliable native Streamlit featured-anime slider."""
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from api import (
    setup, get_top_anime, get_trending, banner_of, poster_of, title_of,
    score_of, year_of, clean_description, grid,
)

setup("Home", "🎌")

st.markdown(
    '<div class="home-intro"><div class="intro-eyebrow">YOUR NEXT OBSESSION STARTS HERE</div>'
    '<h1>Find your <span>next anime.</span></h1>'
    '<p>Explore trending stories, timeless favourites, and hidden gems — all in one place.</p></div>',
    unsafe_allow_html=True,
)

# Refresh the page every five seconds so the featured anime advances automatically.
auto_tick = st_autorefresh(interval=5000, key="aniverse_featured_autorefresh", limit=None)

with st.spinner("Discovering featured anime…"):
    featured = get_top_anime(8)

if featured:
    if "featured_index" not in st.session_state:
        st.session_state.featured_index = 0
    if "featured_last_tick" not in st.session_state:
        st.session_state.featured_last_tick = auto_tick
    elif auto_tick != st.session_state.featured_last_tick:
        tick_delta = max(1, auto_tick - st.session_state.featured_last_tick)
        st.session_state.featured_index = (st.session_state.featured_index + tick_delta) % len(featured)
        st.session_state.featured_last_tick = auto_tick
    index = st.session_state.featured_index % len(featured)
    anime = featured[index]
    title = title_of(anime)
    # Portrait cover art is more consistent than wide/blank banner assets.
    image_url = poster_of(anime) or banner_of(anime)

    st.markdown('<div class="featured-label"><span>✦</span> EDITOR’S PICKS <span class="featured-line"></span><span class="featured-count">FEATURED COLLECTION</span></div>', unsafe_allow_html=True)
    image_col, copy_col = st.columns([1.08, 1.25], gap="large", vertical_alignment="center")
    with image_col:
        if image_url:
            st.image(image_url, use_container_width=True)
        else:
            st.markdown('<div class="image-fallback">🎌<br/>ANIVERSE</div>', unsafe_allow_html=True)
    with copy_col:
        st.markdown(f'<div class="feature-kicker">FEATURED ANIME · {index + 1:02d} / {len(featured):02d}</div>', unsafe_allow_html=True)
        st.markdown(f'<h2 class="feature-heading">{title}</h2>', unsafe_allow_html=True)
        score = score_of(anime)
        year = year_of(anime)
        media_type = anime.get("type") or anime.get("format") or "TV"
        st.markdown(f'<div class="feature-meta"><span>★ {score:.1f}/10</span><i>•</i><span>{year}</span><i>•</i><span>{media_type}</span></div>', unsafe_allow_html=True)
        synopsis = clean_description(anime.get("description"))
        st.markdown(f'<p class="feature-synopsis">{synopsis[:390]}{"…" if len(synopsis) > 390 else ""}</p>', unsafe_allow_html=True)
        genres = anime.get("genres") or []
        if genres:
            st.markdown(" ".join(f'<span class="feature-chip">{g}</span>' for g in genres[:5]), unsafe_allow_html=True)
        st.write("")
        prev_col, next_col, page_col = st.columns([1, 1, 2], gap="small")
        with prev_col:
            if st.button("← Previous", key="featured_prev", use_container_width=True):
                st.session_state.featured_index = (index - 1) % len(featured)
                st.session_state.featured_last_tick = auto_tick
                st.rerun()
        with next_col:
            if st.button("Next →", key="featured_next", type="primary", use_container_width=True):
                st.session_state.featured_index = (index + 1) % len(featured)
                st.session_state.featured_last_tick = auto_tick
                st.rerun()
        with page_col:
            st.caption(f"FEATURE {index + 1} OF {len(featured)}  ·  Auto-plays every 5 seconds")
else:
    st.markdown('<div class="empty-feature"><h3>Featured anime is taking a break.</h3><p>We could not reach AniList right now. Check your connection and retry.</p></div>', unsafe_allow_html=True)
    if st.button("↻ Retry loading anime", type="primary"):
        st.cache_data.clear()
        st.rerun()

st.markdown('<div class="section section-spaced"><div class="section-title">Popular right now <span class="title-spark">✦</span></div><div class="section-sub">What anime fans are watching and talking about.</div></div>', unsafe_allow_html=True)
with st.spinner("Loading popular anime…"):
    popular = get_trending(10)
grid(popular, "home_trending")

st.markdown('<div class="section section-spaced"><div class="section-title">Explore ANIVERSE</div><div class="section-sub">A better way to find your next favourite series.</div></div>', unsafe_allow_html=True)
cols = st.columns(4, gap="medium")
items = [
    ("🔥", "Trending", "See what is popular right now.", "pages/01_Trending.py"),
    ("⭐", "Top Rated", "Discover highly rated favourites.", "pages/02_Top_Rated.py"),
    ("🆕", "New Releases", "Explore the latest seasonal anime.", "pages/03_New_Releases.py"),
    ("🔎", "Search", "Find a series by title or genre.", "pages/04_Search.py"),
]
for col, (icon, title, desc, path) in zip(cols, items):
    with col:
        st.markdown(f'<div class="feature-card"><div class="feature-icon">{icon}</div><div class="feature-title">{title}</div><div class="feature-desc">{desc}</div></div>', unsafe_allow_html=True)
        if st.button(f"Explore {title}  →", key=f"home_{title}", use_container_width=True):
            st.switch_page(path)

st.markdown('<div class="footer">ANIVERSE · Anime Discovery & Recommendation System · Powered by AniList</div>', unsafe_allow_html=True)
