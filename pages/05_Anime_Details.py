import html
import streamlit as st
from api import setup
from api import get_anime_details, poster_of, title_of, score_of, year_of, genres_of, studios_of, clean_description, format_number
setup("Anime Details", "🎬")
anime_id = st.session_state.get("selected_anime_id")
if not anime_id:
    st.info("Choose an anime from Trending, Top Rated, New Releases, or Search to view its details.")
    st.page_link("pages/01_Trending.py", label="🔥 Browse Trending")
    st.stop()
with st.spinner("Loading anime details..."):
    anime = get_anime_details(int(anime_id))
if not anime:
    st.error("Anime details could not be loaded. Please try again.")
    st.stop()
left, right = st.columns([1, 2], gap="large")
with left:
    image = poster_of(anime)
    if image: st.image(image, use_container_width=True)
with right:
    st.markdown(f'<div class="eyebrow">ANIME DETAILS</div><h1 class="detail-title">{html.escape(title_of(anime))}</h1>', unsafe_allow_html=True)
    chips = ''.join(f'<span class="chip">{html.escape(g)}</span>' for g in genres_of(anime)[:6])
    st.markdown(f'<div class="chips"><span class="chip rating">★ {score_of(anime):.1f}/10</span>{chips}</div>', unsafe_allow_html=True)
    stats = st.columns(4)
    for col, value, label in zip(stats, [year_of(anime), anime.get("episodes") or "N/A", anime.get("status") or "N/A", format_number(anime.get("members"))], ["Year", "Episodes", "Status", "Members"]):
        with col: st.markdown(f'<div class="stat"><strong>{html.escape(str(value))}</strong><span>{label}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="synopsis">{html.escape(clean_description(anime.get("description")))}</div>', unsafe_allow_html=True)
    studios = ', '.join(studios_of(anime)) or 'N/A'
    st.markdown(f'<div class="notice"><b>Studio:</b> {html.escape(studios)} &nbsp; · &nbsp; <b>Type:</b> {html.escape(str(anime.get("type", "TV")))} &nbsp; · &nbsp; <b>Source:</b> {html.escape(str(anime.get("source", "Unknown")))}</div>', unsafe_allow_html=True)
    if anime.get("siteUrl"):
        st.link_button("View on MyAnimeList ↗", anime["siteUrl"])
    if st.button("🤖 Get recommendations", use_container_width=True):
        st.session_state["recommendation_source_id"] = anime_id
        st.switch_page("pages/06_Recommendations.py")
