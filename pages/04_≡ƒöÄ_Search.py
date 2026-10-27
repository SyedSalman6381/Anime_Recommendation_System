from api import setup, grid
from api import search_anime
import streamlit as st
setup("Search", "🔎")
st.markdown('<h1 class="eyebrow-title">Search anime</h1><div class="section-sub">Search the live MyAnimeList catalogue by title.</div>', unsafe_allow_html=True)
with st.form("anime_search", clear_on_submit=False):
    query = st.text_input("Anime title", placeholder="Try: Naruto, One Piece, Jujutsu Kaisen...")
    submitted = st.form_submit_button("🔎 Search", use_container_width=True)
if submitted and query.strip():
    with st.spinner("Searching..."):
        st.session_state["search_results"] = search_anime(query, 25)
        st.session_state["search_query"] = query.strip()
if st.session_state.get("search_results"):
    st.markdown(f'<div class="section-title">Results for “{st.session_state.get("search_query", "")}"</div>', unsafe_allow_html=True)
    grid(st.session_state["search_results"], "search")
elif submitted:
    st.warning("No results found. Try another title.")
else:
    st.info("Enter an anime title above to start searching.")
