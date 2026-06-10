import streamlit as st
from utils.constants import CT_PHASES, CT_STATUSES, CT_SPONSORS, CT_STUDY_TYPES

st.title("🔍 ClinicalTrials.gov Search Parameters")
st.markdown("Define separate criteria for analyzing historical experience and tracking active competition. This dual approach ensures precise benchmarking.")

if "study_params" not in st.session_state or not st.session_state.study_params.get("indication"):
    st.warning("⚠️ No study parameters found. Please go back to '1. Planned Study Definition' and define your study first.")
    st.stop()

p = st.session_state.study_params

# Konwersja faz ze Strony 1 na klucze czytelne w UI (zabezpieczenie na wypadek różnic w nazwach)
default_phases_hist = [ph for ph in p.get("phases", []) if ph in CT_PHASES]

with st.form("api_query_form"):
    
    # --- SEKCJA 1: BADANIA HISTORYCZNE ---
    st.header("📚 Historical Studies")
    st.markdown("Filters for assessing country experience, enrollment rates, and finding benchmark studies.")
    
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        h_indication = st.text_input("Indication*", value=p.get("indication", ""), key="h_ind")
        h_phases = st.multiselect("Phases*", options=list(CT_PHASES.keys()), default=default_phases_hist, key="h_pha")
        h_sponsor = st.selectbox("Sponsor Type*", options=list(CT_SPONSORS.keys()), index=list(CT_SPONSORS.keys()).index("Industry"), key="h_spo")
        
    with h_col2:
        h_lookback = st.number_input("Lookback Period (years)*", min_value=1, max_value=20, value=5, step=1, key="h_look")
        h_status = st.multiselect("Study Status*", options=list(CT_STATUSES.keys()), default=["Completed"], key="h_stat")
        h_type = st.selectbox("Study Type*", options=list(CT_STUDY_TYPES.keys()), index=list(CT_STUDY_TYPES.keys()).index("Interventional"), key="h_type")

    st.markdown("---")
    
    # --- SEKCJA 2: KONKURENCJA ---
    st.header("⚔️ Competition")
    st.markdown("Filters for identifying ongoing and planned trials to evaluate site saturation and competition.")
    
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        c_indication = st.text_input("Indication*", value=p.get("indication", ""), key="c_ind")
        c_phases = st.multiselect("Phases*", options=list(CT_PHASES.keys()), default=list(CT_PHASES.keys()), key="c_pha")
        c_sponsor = st.selectbox("Sponsor Type*", options=list(CT_SPONSORS.keys()), index=list(CT_SPONSORS.keys()).index("All"), key="c_spo")
        
    with c_col2:
        c_dates = st.date_input("Study Start and End Date", value=p.get("date_range", ()), key="c_dates")
        c_status = st.multiselect("Study Status*", options=list(CT_STATUSES.keys()), default=["Recruiting", "Not yet recruiting", "Active, not recruiting"], key="c_stat")
        c_type = st.selectbox("Study Type*", options=list(CT_STUDY_TYPES.keys()), index=list(CT_STUDY_TYPES.keys()).index("All"), key="c_type")

    st.markdown("---")
    submitted = st.form_submit_button("Save Search Parameters & Proceed 🚀", type="primary")
    
    if submitted:
        errors = []
        if not h_indication.strip(): errors.append("Historical: Indication")
        if not h_phases: errors.append("Historical: Phases")
        if not h_status: errors.append("Historical: Study Status")
        if not c_indication.strip(): errors.append("Competition: Indication")
        if not c_phases: errors.append("Competition: Phases")
        if not c_status: errors.append("Competition: Study Status")
        
        if errors:
            st.error(f"Please fill in the following mandatory fields: **{', '.join(errors)}**")
        else:
            # Słownik API Query zapisuje przetłumaczone wartości z .constants
            st.session_state.api_query = {
                "historical": {
                    "indication": h_indication,
                    "phases": [CT_PHASES[ph] for ph in h_phases],
                    "sponsor": CT_SPONSORS[h_sponsor],
                    "lookback_years": h_lookback,
                    "status": [CT_STATUSES[st] for st in h_status],
                    "type": CT_STUDY_TYPES[h_type]
                },
                "competition": {
                    "indication": c_indication,
                    "phases": [CT_PHASES[ph] for ph in c_phases],
                    "sponsor": CT_SPONSORS[c_sponsor],
                    "date_range": c_dates,
                    "status": [CT_STATUSES[st] for st in c_status],
                    "type": CT_STUDY_TYPES[c_type]
                }
            }
            st.switch_page("views/3_results.py")