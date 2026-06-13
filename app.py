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
    if "hist_studies_for_ai" not in st.session_state:
        st.session_state.hist_studies_for_ai = []

init_session_state()

# 3. Definicja stron za pomocą st.Page
page_1 = st.Page(
    page="views/1_study_config.py",
    title="1. Planned Study Definition",
    icon="📋",
    default=True
)

page_2 = st.Page(
    page="views/2_criteria_weights.py",
    title="2. Search Criteria",
    icon="🔍"
)

page_3 = st.Page(
    page="views/3_results.py",
    title="3. Weightage and Results",
    icon="📊"
)

# NOWOŚĆ: Definicja dedykowanej strony dla modułu Gemini AI
page_4 = st.Page(
    page="views/4_ai_benchmark.py",
    title="4. AI Benchmark",
    icon="🤖"
)

# 4. Budowa menu nawigacyjnego z uwzględnieniem nowej strony
pg = st.navigation(
    {"Process": [page_1, page_2, page_3, page_4]}
)

# 5. Dodatki w pasku bocznym widoczne na każdej stronie (opcjonalnie)
with st.sidebar:
    st.markdown("---")
    st.caption("Clinical Trials Optimizer v0.1")

# 6. Uruchomienie routingu
pg.run()