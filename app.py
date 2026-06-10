import streamlit as st

# 1. Globalna konfiguracja strony (zawsze jako pierwsze wywołanie Streamlit)
st.set_page_config(
    page_title="Clinical Trials Optimizer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Wstępna inicjalizacja stanu aplikacji (Session State)
# Zapobiega to błędom KeyError, gdy użytkownik przeskakuje między stronami
def init_session_state():
    if "study_params" not in st.session_state:
        st.session_state.study_params = {}
    if "criteria_weights" not in st.session_state:
        st.session_state.criteria_weights = {}
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None

init_session_state()

# 3. Definicja stron za pomocą st.Page
page_1 = st.Page(
    page="views/1_study_config.py",
    title="1. Current Study Configuration",
    icon="📋",
    default=True
)

page_2 = st.Page(
    page="views/2_criteria_weights.py",
    title="2. Search Criteria",
    icon="⚖️"
)

page_3 = st.Page(
    page="views/3_results.py",
    title="3. Weightage and Results",
    icon="📊"
)

# 4. Budowa menu nawigacyjnego
pg = st.navigation(
    {"Process": [page_1, page_2, page_3]}
)

# 5. Dodatki w pasku bocznym widoczne na każdej stronie (opcjonalnie)
with st.sidebar:
    st.markdown("---")
    st.caption("Clinical Trials Optimizer v0.1")

# 6. Uruchomienie routingu
pg.run()