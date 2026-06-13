import streamlit as st
import pandas as pd

st.title("🤖 Comprehensive AI & Operational Benchmarking")
st.markdown("Analyze all historical trials side-by-side with calculated enrollment metrics and AI-driven criteria similarity scoring.")

planned_study = st.session_state.get("study_params", {})
hist_studies = st.session_state.get("hist_studies_for_ai", [])

if not planned_study or not hist_studies:
    st.warning("⚠️ Missing data for Analysis. Please run the search on previous pages first.")
    st.stop()

# ==========================================
# SEKCJA WALIDACJI: OSTRZEŻENIE O LIMICIE AI
# ==========================================
if len(hist_studies) > 100:
    st.warning(
        "⚠️ **Volume Warning: AI Analysis Limit Exceeded!**\n\n"
        f"Found **{len(hist_studies)}** historical trials, but the AI engine is capped at the top **100** most recent "
        "protocols to avoid data overflow. To secure full-matrix coverage and eliminate noise, it is highly "
        "recommended to go back to **'2. Search Criteria'** and tighten your historical filters "
        "(e.g., select specific study phases, enforce an industry sponsor, or use a shorter lookback date)."
    )

def build_comprehensive_dataframe(studies):
    if not studies:
        return pd.DataFrame()
    
    data = []
    for s in studies:
        protocol = s.get("protocolSection", {})
        
        ident = protocol.get("identificationModule", {})
        nct_id = ident.get("nctId", "N/A")
        title = ident.get("briefTitle", "N/A")
        
        status_mod = protocol.get("statusModule", {})
        start_date = status_mod.get("startDateStruct", {}).get("date", "N/A")
        pcd = status_mod.get("primaryCompletionDateStruct", {}).get("date", "N/A")
        
        design = protocol.get("designModule", {})
        patients = design.get("enrollmentInfo", {}).get("count", None)
        
        locations_list = protocol.get("contactsLocationsModule", {}).get("locations", [])
        num_sites = len(locations_list)
        
        raw_criteria = protocol.get("eligibilityModule", {}).get("eligibilityCriteria", "")
        inc_criteria, exc_criteria = "N/A", "N/A"
        
        if raw_criteria:
            if "Exclusion Criteria:" in raw_criteria:
                parts = raw_criteria.split("Exclusion Criteria:")
                inc_criteria = parts[0].replace("Inclusion Criteria:", "").strip()
                exc_criteria = parts[1].strip()
            elif "Inclusion Criteria:" in raw_criteria:
                inc_criteria = raw_criteria.replace("Inclusion Criteria:", "").strip()
            else:
                inc_criteria = raw_criteria

        period_months, enrollment_rate = None, None
        try:
            dt_start = pd.to_datetime(start_date, errors='coerce')
            dt_pcd = pd.to_datetime(pcd, errors='coerce')
            
            if pd.notnull(dt_start) and pd.notnull(dt_pcd) and dt_pcd > dt_start:
                days = (dt_pcd - dt_start).days
                period_months = round(days / 30.44, 1)
                
                if period_months > 0 and num_sites > 0 and isinstance(patients, (int, float)):
                    enrollment_rate = round(patients / num_sites / period_months, 2)
        except:
            pass

        data.append({
            "NCT ID": nct_id,
            "Title": title,
            "Inclusion Criteria": inc_criteria,
            "Exclusion Criteria": exc_criteria,
            "Similarity Score (%)": None, 
            "AI Explanation": "Pending AI Analysis...",
            "Patients": patients,
            "Sites": num_sites,
            "Enrollment Months": period_months,
            "ER (Pts/Site/Mon)": enrollment_rate
        })
    return pd.DataFrame(data)

if "comprehensive_table" not in st.session_state or len(st.session_state.comprehensive_table) != len(hist_studies):
    st.session_state.comprehensive_table = build_comprehensive_dataframe(hist_studies)

with st.expander("🎯 View Your Planned Study Baseline", expanded=False):
    st.markdown(f"**Title:** {planned_study.get('title', 'N/A')}")
    st.markdown(f"**Indication:** {planned_study.get('indication', 'N/A')}")
    st.markdown(f"**Inclusion:** {planned_study.get('inclusion_criteria', 'N/A')}")
    st.markdown(f"**Exclusion:** {planned_study.get('exclusion_criteria', 'N/A')}")

st.markdown(f"### 📋 Historical Trials Matrix ({len(hist_studies)} trials)")
st.markdown("Below is the complete grid. Click the button to populate the AI similarity columns for the top 100 most relevant trials.")

st.dataframe(
    st.session_state.comprehensive_table, 
    use_container_width=True, 
    hide_index=True,
    column_config={
        "Similarity Score (%)": st.column_config.NumberColumn(
            "Similarity Score (%)",
            format="%d %%", 
            help="AI generated match score"
        ),
        "AI Explanation": st.column_config.TextColumn(
            "AI Explanation",
            width="large", 
            help="Double-click cell to expand text"
        )
    }
)

if st.button("🧠 Run AI Matrix Scoring (Gemini)", type="primary", use_container_width=True):
    with st.spinner("Gemini is processing protocols and computing scores for the matrix..."):
        from services.gemini_benchmark import run_ai_table_scoring
        
        ai_results = run_ai_table_scoring(planned_study, hist_studies)
        
        if ai_results:
            ai_map = {item["nct_id"]: item for item in ai_results if "nct_id" in item}
            
            df_updated = st.session_state.comprehensive_table.copy()
            for idx, row in df_updated.iterrows():
                nct = row["NCT ID"]
                if nct in ai_map:
                    score = ai_map[nct].get('similarity_score')
                    if score is not None:
                        df_updated.at[idx, "Similarity Score (%)"] = float(score)
                    df_updated.at[idx, "AI Explanation"] = ai_map[nct].get('explanation', 'N/A')
            
            st.session_state.comprehensive_table = df_updated
            st.success("✅ Matrix successfully updated with Gemini Insights!")
            st.rerun()
        else:
            st.error("⚠️ Failed to parse AI results. Ensure your API key is correct and try again.")