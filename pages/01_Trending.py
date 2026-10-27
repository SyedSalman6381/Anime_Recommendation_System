from api import setup, grid
from api import get_trending
import streamlit as st
setup("Trending", "🔥")
st.markdown('<h1 class="eyebrow-title">Trending anime</h1><div class="section-sub">Popular titles based on current MyAnimeList popularity rankings.</div>', unsafe_allow_html=True)
with st.spinner("Loading trending anime..."):
    anime = get_trending(25)
grid(anime, "trending")
