from api import setup, grid
from api import get_current_season, current_season
import streamlit as st
setup("New Releases", "🆕")
st.markdown(f'<h1 class="eyebrow-title">New releases</h1><div class="section-sub">Anime airing in the current {current_season()} season.</div>', unsafe_allow_html=True)
with st.spinner("Loading the current season..."):
    anime = get_current_season(25)
grid(anime, "new")
