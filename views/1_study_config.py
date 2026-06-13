import streamlit as st
import datetime
from utils.constants import CT_PHASES, CT_SPONSORS

st.title("📋 Planned Study Definition")
st.markdown("Define the parameters of the study you want to conduct. This profile will serve as a baseline for comparing historical data and finding the optimal countries.")

default_params = {
    "title": "",
    "indication": "",
    "sponsor_type": "Industry (Commercial)",
    "phases": ["Phase 1"],
    "date_range": (),
    "num_patients": 0,
    "num_sites": 0,
    "inclusion_criteria": "",
    "exclusion_criteria": "",
    "countries": []
}

if "study_params" not in st.session_state or not st.session_state.study_params:
    st.session_state.study_params = default_params

p = st.session_state.study_params

phase_options = list(CT_PHASES.keys())
sponsor_options = list(CT_SPONSORS.keys())

saved_sponsor = p.get("sponsor_type", "Industry (Commercial)")
sponsor_idx = sponsor_options.index(saved_sponsor) if saved_sponsor in sponsor_options else 0

saved_phase_list = p.get("phases", ["Phase 1"])
saved_phase = saved_phase_list[0] if saved_phase_list and saved_phase_list[0] in phase_options else phase_options[0]
phase_idx = phase_options.index(saved_phase)

with st.form("study_config_form"):
    title = st.text_input("Study Title*", value=p.get("title", ""))
    
    col1, col2 = st.columns(2)
    with col1:
        indication = st.text_input(
            "Indication (e.g., Oncology, Diabetes)*", 
            value=p.get("indication", "")
        )
        phase = st.selectbox(
            "Phase*", 
            options=phase_options,
            index=phase_idx
        )
        
    with col2:
        sponsor_type = st.selectbox(
            "Sponsor Type", 
            options=sponsor_options,
            index=sponsor_idx
        )
        date_range = st.date_input(
            "Study Start and End Date", 
            value=p.get("date_range", ()),
            help="Select the start and end dates by clicking twice on the calendar."
        )

    col3, col4 = st.columns(2)
    with col3:
        num_patients = st.number_input(
            "Number of Patients", 
            min_value=0, 
            step=10, 
            value=p.get("num_patients", 0)
        )
    with col4:
        num_sites = st.number_input(
            "Number of Sites", 
            min_value=0, 
            step=1, 
            value=p.get("num_sites", 0)
        )

    available_countries = [
        "Poland", "Germany", "Spain", "France", "USA", 
        "United Kingdom", "Czech Republic", "Hungary", "Romania"
    ]
    countries = st.multiselect(
        "Target Countries", 
        options=available_countries,
        default=p.get("countries", [])
    )

    inclusion_criteria = st.text_area(
        "Inclusion Criteria", 
        value=p.get("inclusion_criteria", ""),
        height=150
    )
    
    exclusion_criteria = st.text_area(
        "Exclusion Criteria", 
        value=p.get("exclusion_criteria", ""),
        height=150
    )

    submitted = st.form_submit_button("Save Study Definition", type="primary")

    if submitted:
        missing_fields = []
        if not title.strip(): missing_fields.append("Study Title")
        if not indication.strip(): missing_fields.append("Indication")

        if missing_fields:
            st.error(f"Please fill in the mandatory fields: **{', '.join(missing_fields)}**")
        else:
            st.session_state.study_params = {
                "title": title,
                "indication": indication,
                "sponsor_type": sponsor_type,
                "phases": [phase],
                "date_range": date_range,
                "num_patients": num_patients,
                "num_sites": num_sites,
                "inclusion_criteria": inclusion_criteria,
                "exclusion_criteria": exclusion_criteria,
                "countries": countries
            }
            st.switch_page("views/2_criteria_weights.py")