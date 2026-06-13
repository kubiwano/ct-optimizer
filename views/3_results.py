import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

from api.ctgov_client import CTGovClient
from services.data_aggregator import aggregate_country_metrics

st.title("📊 Optimization Results & Ranking")
st.markdown("Analyze the scoring of potential countries based on **live ClinicalTrials.gov data**.")

api_query = st.session_state.get("api_query", {})
if not api_query:
    st.warning("⚠️ No API parameters found. Please go back to '2. API Query & Criteria' and configure your search.")
    st.stop()

@st.cache_data(show_spinner=False)
def fetch_and_process_data(query_params):
    hist_params = query_params["historical"]
    comp_params = query_params["competition"]
    
    min_comp_pcd = None
    if comp_params.get("remove_past_pcd"):
        planned_study = st.session_state.get("study_params", {})
        planned_dates = planned_study.get("date_range", ())
        
        if isinstance(planned_dates, (tuple, list)) and len(planned_dates) > 0:
            min_comp_pcd = planned_dates[0].strftime("%Y-%m-%d")
        elif isinstance(planned_dates, datetime.date):
            min_comp_pcd = planned_dates.strftime("%Y-%m-%d")
        else:
            min_comp_pcd = datetime.date.today().strftime("%Y-%m-%d")

    hist_studies = CTGovClient.fetch_studies(
        query_name="Historical",
        condition=hist_params["indication"],
        phases=hist_params["phases"],
        sponsor=hist_params["sponsor"],
        statuses=hist_params["status"],
        start_date=hist_params.get("start_date"),
        limit=1000 
    )
    
    comp_studies = CTGovClient.fetch_studies(
        query_name="Competition",
        condition=comp_params["indication"],
        phases=comp_params["phases"],
        sponsor=comp_params["sponsor"],
        statuses=comp_params["status"],
        start_date=None, 
        min_primary_completion_date=min_comp_pcd,
        limit=1000
    )
    
    df_agg = aggregate_country_metrics(hist_studies, comp_studies)
    return df_agg, hist_studies, comp_studies

# --- ZAKTUALIZOWANY PARSER JSON: Pełne spektrum kolumn + Wyliczenia ---
def build_study_dataframe(studies):
    if not studies:
        return pd.DataFrame()
    
    data = []
    for s in studies:
        protocol = s.get("protocolSection", {})
        
        # 1. Identyfikacja i Podstawy
        ident = protocol.get("identificationModule", {})
        nct_id = ident.get("nctId", "N/A")
        title = ident.get("briefTitle", "N/A")
        
        status_mod = protocol.get("statusModule", {})
        status = status_mod.get("overallStatus", "N/A")
        start_date = status_mod.get("startDateStruct", {}).get("date", "N/A")
        pcd = status_mod.get("primaryCompletionDateStruct", {}).get("date", "N/A")
        end_date = status_mod.get("completionDateStruct", {}).get("date", "N/A")
        
        design = protocol.get("designModule", {})
        phases = ", ".join(design.get("phases", [])) if design.get("phases") else "N/A"
        conditions = ", ".join(protocol.get("conditionsModule", {}).get("conditions", []))
        
        # 2. Dane operacyjne (Pacjenci, Ośrodki, Kraje)
        patients = design.get("enrollmentInfo", {}).get("count", "N/A")
        
        locations_list = protocol.get("contactsLocationsModule", {}).get("locations", [])
        num_sites = len(locations_list)
        countries_set = set([loc.get("country") for loc in locations_list if loc.get("country")])
        countries_str = ", ".join(sorted(countries_set)) if countries_set else "N/A"
        
        # 3. Inteligentne rozbijanie sekcji Kryteriów (Inclusion / Exclusion)
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

        # Skracanie tekstu kryteriów na potrzeby widoku tabelarycznego
        inc_short = inc_criteria[:120] + "..." if len(inc_criteria) > 120 else inc_criteria
        exc_short = exc_criteria[:120] + "..." if len(exc_criteria) > 120 else exc_criteria

        # 4. Matematyka Rekrutacji: Enrollment Period & Enrollment Rate
        period_months, enrollment_rate = "N/A", "N/A"
        try:
            dt_start = pd.to_datetime(start_date, errors='coerce')
            dt_pcd = pd.to_datetime(pcd, errors='coerce')
            
            if pd.notnull(dt_start) and pd.notnull(dt_pcd) and dt_pcd > dt_start:
                days = (dt_pcd - dt_start).days
                period_months = round(days / 30.44, 1)
                
                if period_months > 0 and isinstance(patients, (int, float)):
                    enrollment_rate = round(patients / period_months, 2)
        except:
            pass

        data.append({
            "NCT ID": nct_id,
            "Title": title,
            "Status": status,
            "Phases": phases,
            "Conditions": conditions,
            "Start Date": start_date,
            "Primary Completion": pcd,
            "Study End Date": end_date,
            "Patients Enrolled": patients,
            "Number of Sites": num_sites,
            "Countries": countries_str,
            "Enrollment Period (Months)": period_months,
            "Enrollment Rate (Pts/Mon)": enrollment_rate,
            "Inclusion Criteria": inc_short,
            "Exclusion Criteria": exc_short
        })
    return pd.DataFrame(data)

# --- ZAKTUALIZOWANE METRYKI: Tylko czysty, szary tekst tekstowy ---
def render_table_metrics(df, is_historical=False):
    if df.empty:
        return
        
    unique_ids = df["NCT ID"].nunique()
    statuses = [str(s) for s in df["Status"].unique() if s != "N/A"]
    
    phases_set = set()
    for p in df["Phases"]:
        if p != "N/A":
            phases_set.update([x.strip() for x in str(p).split(",")])
            
    valid_starts = pd.to_datetime(df[df["Start Date"] != "N/A"]["Start Date"], errors='coerce').dropna()
    min_start = valid_starts.min().strftime('%Y-%m-%d') if not valid_starts.empty else "N/A"
    max_start = valid_starts.max().strftime('%Y-%m-%d') if not valid_starts.empty else "N/A"

    valid_pcd = pd.to_datetime(df[df["Primary Completion"] != "N/A"]["Primary Completion"], errors='coerce').dropna()
    
    # Renderowanie szarych linii opisu (Zgodnie z życzeniem - brak st.metric)
    st.caption(f"**Unique Trials:** {unique_ids}")
    st.caption(f"**Start Date Range:** From {min_start} to {max_start}")
    
    if is_historical:
        # Dla historycznych szukamy MAX Completion Date
        max_pcd = valid_pcd.max().strftime('%Y-%m-%d') if not valid_pcd.empty else "N/A"
        st.caption(f"**Max Primary Completion Date:** {max_pcd}")
    else:
        # Dla konkurencji zostawiamy MIN Completion Date
        min_pcd = valid_pcd.min().strftime('%Y-%m-%d') if not valid_pcd.empty else "N/A"
        st.caption(f"**Min Primary Completion Date:** {min_pcd}")
        
    st.caption(f"**Distinct Statuses:** {', '.join(statuses) if statuses else 'N/A'}")
    st.caption(f"**Distinct Phases:** {', '.join(sorted(phases_set)) if phases_set else 'N/A'}")
    st.markdown("<br>", unsafe_allow_html=True)

with st.spinner("🌍 Fetching live data from ClinicalTrials.gov and calculating metrics..."):
    df_metrics, hist_studies, comp_studies = fetch_and_process_data(api_query)

if df_metrics.empty:
    st.error("No locations found for the provided search criteria. Try broadening your search parameters.")
    st.stop()

# 1. Globalne statystyki zapytania
st.markdown("---")
st.subheader("📈 Global API Insights")
col_m1, col_m2 = st.columns(2)
col_m1.metric("📚 Total Historical Studies Analyzed", len(hist_studies))
col_m2.metric("⚔️ Total Active/Competing Studies Found", len(comp_studies))

# 2. Sekcje audytu danych (Expandery z nowym szarym UI i dodatkowymi kolumnami)
with st.expander("🔎 View Raw Data: Historical Studies"):
    st.markdown("Verify the exact trials and calculated enrollment baselines fetched by your historical parameters.")
    df_hist_raw = build_study_dataframe(hist_studies)
    render_table_metrics(df_hist_raw, is_historical=True) # Przekazujemy flagę historii
    st.dataframe(df_hist_raw, use_container_width=True, hide_index=True)

with st.expander("🔎 View Raw Data: Competition Studies"):
    st.markdown("Verify the active/planned pipelines saturation fetched by your competition parameters.")
    df_comp_raw = build_study_dataframe(comp_studies)
    render_table_metrics(df_comp_raw, is_historical=False)
    st.dataframe(df_comp_raw, use_container_width=True, hide_index=True)

# 3. Interfejs manualnego wprowadzania wag
st.markdown("---")
st.subheader("⚖️ Set Criteria Weights")

col_w1, col_w2, col_w3, col_w4 = st.columns(4)
with col_w1:
    w_exp = st.number_input("Experience (Completed)", min_value=0, value=8, step=1)
with col_w2:
    w_speed = st.number_input("Approval Speed", min_value=0, value=7, step=1)
with col_w3:
    w_cost = st.number_input("Cost Efficiency", min_value=0, value=6, step=1)
with col_w4:
    w_comp = st.number_input("Low Competition", min_value=0, value=5, step=1)

total_weight = w_exp + w_speed + w_cost + w_comp

if total_weight == 0:
    st.error("Total weight cannot be zero. Please enter values above 0 to see the ranking.")
    st.stop()
else:
    st.info(
        f"**Weight Distribution:** "
        f"Experience: **{w_exp/total_weight:.1%}** | "
        f"Speed: **{w_speed/total_weight:.1%}** | "
        f"Cost: **{w_cost/total_weight:.1%}** | "
        f"Competition: **{w_comp/total_weight:.1%}**"
    )

# 4. Silnik obliczeniowy
df_results = df_metrics.copy()

df_results["Final Score"] = (
    (df_results["Historical Experience"] * w_exp) +
    (df_results["Approval Speed"] * w_speed) +
    (df_results["Cost Efficiency"] * w_cost) +
    (df_results["Low Competition"] * w_comp)
) / total_weight

df_results = df_results.sort_values(by="Final Score", ascending=False).reset_index(drop=True)
df_results.index = df_results.index + 1

for col in ["Final Score", "Historical Experience", "Approval Speed", "Cost Efficiency", "Low Competition"]:
    df_results[col] = df_results[col].round(3)

# 5. Interaktywna Tabela Wyników
st.markdown("---")
st.subheader("🏆 Recommended Countries Ranking")
st.markdown("👉 **Click on any row** to see the detailed performance profile for that country.")

selection_event = st.dataframe(
    df_results,
    use_container_width=True,
    selection_mode="single-row",
    on_select="rerun"
)

top_country = df_results.iloc[0]["Country"]
top_score = df_results.iloc[0]["Final Score"]
st.success(f"**System Recommendation:** The optimal choice is **{top_country}** with a score of **{top_score:.3f}**.")

# 6. Szczegóły Kraju (Radar Chart)
st.markdown("---")

selected_rows = selection_event.selection.rows
if selected_rows:
    selected_idx = selected_rows[0]
    selected_country = df_results.iloc[selected_idx]["Country"]
else:
    selected_country = top_country

st.subheader(f"🕸️ Country Deep Dive: {selected_country}")

country_data = df_results[df_results["Country"] == selected_country].iloc[0]
categories = ["Historical Experience", "Approval Speed", "Cost Efficiency", "Low Competition"]
values = [country_data[cat] for cat in categories]

df_radar = pd.DataFrame(dict(r=values, theta=categories))

fig = px.line_polar(
    df_radar, 
    r='r', 
    theta='theta', 
    line_close=True,
    range_r=[0, 1.0],
)
fig.update_traces(fill='toself', line_color='#4CAF50')

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. PRZEJŚCIE DO ANALIZY AI
# ==========================================
st.markdown("---")
st.subheader("🤖 Next Step: AI Benchmark Analysis")
st.markdown("Proceed to the dedicated AI module to find the most similar historical trials using Google Gemini.")

# Zapisujemy pobrane badania do sesji, żeby Strona 4 nie musiała znowu odpytywać API
st.session_state.hist_studies_for_ai = hist_studies

if st.button("Go to AI Benchmark 🚀", type="primary"):
    st.switch_page("views/4_ai_benchmark.py")