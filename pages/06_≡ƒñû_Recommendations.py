import streamlit as st
from api import setup, grid
from api import get_anime_details, build_recommendation_pool, title_of
from recommender import rank_candidates
setup("Recommendations", "🤖")
anime_id = st.session_state.get("recommendation_source_id") or st.session_state.get("selected_anime_id")
if not anime_id:
    st.info("Open an anime first, then choose “Get recommendations”.")
    st.page_link("pages/04_🔎_Search.py", label="🔎 Search for an anime")
    st.stop()
selected = get_anime_details(int(anime_id))
if not selected:
    st.error("The selected anime could not be loaded.")
    st.stop()
st.markdown(f'<h1 class="eyebrow-title">Because you liked {title_of(selected)}</h1><div class="section-sub">Hybrid recommendations using genre, themes, synopsis similarity, studio, rating, episodes and community signals.</div>', unsafe_allow_html=True)
with st.spinner("Finding similar anime..."):
    pool = build_recommendation_pool(int(anime_id))
    ranked = rank_candidates(selected, pool, top_n=15)
if not ranked:
    st.warning("Not enough data was available to generate recommendations right now.")
    st.stop()
results = [item["anime"] for item in ranked]
grid(results, "recommendation", ranked)
