"""Settings — company defaults, file paths, and preferences."""

import streamlit as st
from pathlib import Path
from settings_ui import render_settings_workspace

ROOT = Path(__file__).resolve().parent.parent
lang = st.session_state.get('lang', 'en')

render_settings_workspace(ROOT, lang)
