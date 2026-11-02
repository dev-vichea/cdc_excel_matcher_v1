"""CDC Customs & Quota Manager — Web Platform Entry Point.

Centralized system for import/export shipment tracking, CDC quota matching,
official permit generation, and monthly cut-stock in-place updates.
"""

from pathlib import Path
import streamlit as st

from services.i18n import get_font_css, t
from services.settings_store import get_default_cdc_path, get_settings

ROOT = Path(__file__).parent

st.set_page_config(
    page_title="CDC Customs & Quota Manager",
    page_icon=":material/inventory_2:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Typography & Kantumruy Pro Font Setup ─────────────────────
_font_face = get_font_css()
_custom_css = """
    /* Ensure Material Symbols icon glyphs are never overridden */
    [data-testid="stIconMaterial"], 
    .material-symbols-rounded, 
    .material-icons,
    [class*="material-symbols"],
    [data-testid*="Icon"],
    span[translate="no"] {
        font-family: "Material Symbols Rounded", "Material Icons" !important;
        font-feature-settings: "liga" 1 !important;
    }

    /* Khmer + English typography */
    html, body, .stApp,
    p, label, input, textarea, select,
    .stMarkdown, .stMarkdown *,
    [data-testid="stWidgetLabel"],
    [data-testid="stMetricLabel"],
    [data-testid="stExpander"] summary {
        font-family: 'Kantumruy Pro', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }
"""

st.markdown(f"<style>\n{_font_face}\n{_custom_css}\n</style>", unsafe_allow_html=True)

# ── Sidebar Brand & Language ──────────────────────────────────
with st.sidebar:
    st.markdown("### :material/inventory_2: CDC Customs OS")
    st.caption("Cambodia Duty Exemption & Cut-Stock")

    lang_choice = st.selectbox(
        "Language / ភាសា",
        ["English", "ភាសាខ្មែរ (Khmer)"],
        index=0 if st.session_state.get("lang", "en") == "en" else 1,
        label_visibility="collapsed",
    )
    lang = "km" if "ខ្មែរ" in lang_choice else "en"
    st.session_state["lang"] = lang

# ── Multi-Page Navigation ─────────────────────────────────────
pages = {
    "Operations": [
        st.Page("app_pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
        st.Page("app_pages/import_matcher.py", title="Import matcher", icon=":material/sync_alt:"),
        st.Page("app_pages/batch_cutstock.py", title="Batch cut-stock", icon=":material/layers:"),
        st.Page("app_pages/shipments.py", title="Shipments", icon=":material/local_shipping:"),
    ],
    "Master data": [
        st.Page("app_pages/cdc_master.py", title="CDC quotas", icon=":material/verified:"),
        st.Page("app_pages/settings.py", title="Settings", icon=":material/settings:"),
    ],
}

nav = st.navigation(pages, position="sidebar")

# Top header for current page
st.title(nav.title, icon=nav.icon)

nav.run()
