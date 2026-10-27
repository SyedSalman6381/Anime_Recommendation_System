from api import setup, grid
from api import get_top_anime
import streamlit as st
setup("Top Rated", "⭐")
st.markdown('<h1 class="eyebrow-title">Top rated</h1><div class="section-sub">Highly rated anime from the MyAnimeList catalogue.</div>', unsafe_allow_html=True)
with st.spinner("Loading top-rated anime..."):
    anime = sorted(get_top_anime(25), key=lambda x: x.get("averageScore", 0), reverse=True)
grid(anime, "rated")
