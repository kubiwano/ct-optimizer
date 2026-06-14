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
    st.warning("⚠️ No parameters found. Please go back to '2. Search Criteria' and configure your search.")
    st.stop()

# ==========================================
# 1. ARCHITEKTURA POBIERANIA (ZOPTYMALIZOWANY CACHE)
# ==========================================
@st.cache_data(show_spinner=False)
def fetch_api_data(query_params):
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
    
    return hist_studies, comp_studies

# --- PARSER JSON ---
def build_study_dataframe(studies):
    if not studies:
        return pd.DataFrame()
    
    data = []
    for s in studies:
        protocol = s.get("protocolSection", {})
        
        ident = protocol.get("identificationModule", {})
        nct_id = ident.get("nctId", "N/A")
        title = ident.get("briefTitle", "N/A")
        
        sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
        sponsor = sponsor_mod.get("leadSponsor", {}).get("name", "N/A")
        
        status_mod = protocol.get("statusModule", {})
        status = status_mod.get("overallStatus", "N/A")
        start_date = status_mod.get("startDateStruct", {}).get("date", "N/A")
        pcd = status_mod.get("primaryCompletionDateStruct", {}).get("date", "N/A")
        end_date = status_mod.get("completionDateStruct", {}).get("date", "N/A")
        
        design = protocol.get("designModule", {})
        phases = ", ".join(design.get("phases", [])) if design.get("phases") else "N/A"
        conditions = ", ".join(protocol.get("conditionsModule", {}).get("conditions", []))
        
        patients = design.get("enrollmentInfo", {}).get("count", "N/A")
        
        locations_list = protocol.get("contactsLocationsModule", {}).get("locations", [])
        num_sites = len(locations_list)
        countries_set = set([loc.get("country") for loc in locations_list if loc.get("country")])
        countries_str = ", ".join(sorted(countries_set)) if countries_set else "N/A"
        
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

        inc_short = inc_criteria[:120] + "..." if len(inc_criteria) > 120 else inc_criteria
        exc_short = exc_criteria[:120] + "..." if len(exc_criteria) > 120 else exc_criteria

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
            "Sponsor": sponsor,
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

# --- METRYKI ---
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
    
    st.caption(f"**Unique Trials:** {unique_ids}")
    st.caption(f"**Start Date Range:** From {min_start} to {max_start}")
    
    if is_historical:
        max_pcd = valid_pcd.max().strftime('%Y-%m-%d') if not valid_pcd.empty else "N/A"
        st.caption(f"**Max Primary Completion Date:** {max_pcd}")
    else:
        min_pcd = valid_pcd.min().strftime('%Y-%m-%d') if not valid_pcd.empty else "N/A"
        st.caption(f"**Min Primary Completion Date:** {min_pcd}")
        
    st.caption(f"**Distinct Statuses:** {', '.join(statuses) if statuses else 'N/A'}")
    st.caption(f"**Distinct Phases:** {', '.join(sorted(phases_set)) if phases_set else 'N/A'}")
    st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 2. POBRANIE DANYCH I AGREGACJA W LOCIE
# ==========================================
with st.spinner("🌍 Fetching live data from ClinicalTrials.gov and calculating metrics..."):
    hist_studies, comp_studies = fetch_api_data(api_query)
    selected_benchmarks = st.session_state.get("selected_benchmarks", [])
    df_metrics = aggregate_country_metrics(hist_studies, comp_studies, selected_benchmarks)

if df_metrics.empty:
    st.error("No locations found for the provided search criteria. Try broadening your search parameters.")
    st.stop()

# 1. Globalne statystyki zapytania
st.markdown("---")
col_m1, col_m2 = st.columns(2)
col_m1.metric("📚 Total Historical Studies Analyzed", len(hist_studies))
col_m2.metric("⚔️ Total Active/Competing Studies Found", len(comp_studies))

# 2. Sekcje audytu danych
with st.expander("🔎 View Raw Data: Historical Studies"):
    st.markdown("Verify the exact trials and calculated enrollment baselines fetched by your historical parameters.")
    df_hist_raw = build_study_dataframe(hist_studies)
    render_table_metrics(df_hist_raw, is_historical=True)
    st.dataframe(df_hist_raw, use_container_width=True, hide_index=True)

with st.expander("🔎 View Raw Data: Competition Studies"):
    st.markdown("Verify the active/planned pipelines saturation fetched by your competition parameters.")
    df_comp_raw = build_study_dataframe(comp_studies)
    render_table_metrics(df_comp_raw, is_historical=False)
    st.dataframe(df_comp_raw, use_container_width=True, hide_index=True)

# 3. Interfejs manualnego wprowadzania wag
st.markdown("---")
st.subheader("⚖️ Set Criteria Weights")

col_w1, col_w2, col_w3, col_w4, col_w5 = st.columns(5)
with col_w1:
    w_exp = st.number_input("1. General Experience", min_value=0, value=5, step=1)
with col_w2:
    w_spec_exp = st.number_input("2. Specific (Gold) Exp", min_value=0, value=8, step=1, help="Weight applied ONLY to the countries that participated in your selected AI Benchmark trials.")
with col_w3:
    w_speed = st.number_input("3. Approval Speed", min_value=0, value=7, step=1)
with col_w4:
    w_cost = st.number_input("4. Cost Efficiency", min_value=0, value=6, step=1)
with col_w5:
    w_comp = st.number_input("5. Low Competition", min_value=0, value=5, step=1)

total_weight = w_exp + w_spec_exp + w_speed + w_cost + w_comp

if total_weight == 0:
    st.error("Total weight cannot be zero. Please enter values above 0 to see the ranking.")
    st.stop()
else:
    st.info(
        f"**Weight Distribution:** "
        f"1. Gen. Exp: **{w_exp/total_weight:.1%}** | "
        f"2. Spec. Exp: **{w_spec_exp/total_weight:.1%}** | "
        f"3. Speed: **{w_speed/total_weight:.1%}** | "
        f"4. Cost: **{w_cost/total_weight:.1%}** | "
        f"5. Competition: **{w_comp/total_weight:.1%}**"
    )

if selected_benchmarks:
    st.success(f"🎯 **Gold Standard AI Benchmarks Active:** The algorithm is currently emphasizing specific experience from **{len(selected_benchmarks)}** manually selected benchmark trials.")

# ==========================================
# 4. SILNIK OBLICZENIOWY (ZAKTUALIZOWANY)
# ==========================================
df_results = df_metrics.copy()

# Wyliczenie wyniku końcowego na bazie zaktualizowanych nazw
df_results["Final Score"] = (
    (df_results["1. Gen. Exp Score"] * w_exp) +
    (df_results["2. Spec. Exp Score"] * w_spec_exp) +
    (df_results["3. Speed Score"] * w_speed) +
    (df_results["4. Cost Score"] * w_cost) +
    (df_results["5. Low Comp. Score"] * w_comp)
) / total_weight

# Sortowanie malejące po Final Score
df_results = df_results.sort_values(by="Final Score", ascending=False).reset_index(drop=True)

# Dodanie Rankingu (Pozycja)
df_results.insert(0, 'Rank', range(1, len(df_results) + 1))

# Kategoryzacja Tierów (Top 10: High, 11-20: Medium, 21-30: Low)
def assign_tier(rank):
    if rank <= 10:
        return "Tier 1 (High)"
    elif rank <= 20:
        return "Tier 2 (Medium)"
    elif rank <= 30:
        return "Tier 3 (Low)"
    else:
        return "Not Classified"

df_results.insert(1, 'Tier', df_results['Rank'].apply(assign_tier))

# Formatowanie zaokrągleń dla Score'ów
score_cols = ["Final Score", "1. Gen. Exp Score", "2. Spec. Exp Score", "3. Speed Score", "4. Cost Score", "5. Low Comp. Score"]
for col in score_cols:
    if col in df_results.columns:
        df_results[col] = df_results[col].round(3)

# Porządkowanie widoku tabeli (Pary: Liczba -> Score)
ordered_cols = [
    "Rank", "Tier", "Country", "Final Score",
    "1. Historical Trials (Count)", "1. Gen. Exp Score",
    "2. Gold Standard Trials (Count)", "2. Spec. Exp Score",
    "3. Est. Approval Time (Days)", "3. Speed Score",
    "4. Est. Cost per Patient ($)", "4. Cost Score",
    "5. Active Trials (Count)", "5. Low Comp. Score"
]
df_results = df_results[ordered_cols]


# 5. Interaktywna Tabela Wyników
st.markdown("---")
st.subheader("🏆 Recommended Countries Ranking")
st.markdown("👉 **Click on any row** to see the detailed performance profile for that country.")

selection_event = st.dataframe(
    df_results,
    use_container_width=True,
    selection_mode="single-row",
    on_select="rerun",
    hide_index=True # Ukrywamy brzydki index boczny, bo mamy Rank!
)

top_country = df_results.iloc[0]["Country"]
top_score = df_results.iloc[0]["Final Score"]
st.success(f"**System Recommendation:** The optimal choice is **{top_country}** with a score of **{top_score:.3f}**.")

# ==========================================
# 6. SZCZEGÓŁY KRAJU (DEEP DIVE + RADAR)
# ==========================================
st.markdown("---")

selected_rows = selection_event.selection.rows
if selected_rows:
    selected_idx = selected_rows[0]
    selected_country = df_results.iloc[selected_idx]["Country"]
else:
    selected_country = top_country

st.subheader(f"🕸️ Country Deep Dive: {selected_country}")

# Wyliczamy lokalne rankingi dla parametrów zaktualizowanych o nową nomenklaturę
ranks = df_results.copy()
for col in score_cols:
    if col in ranks.columns:
        ranks[f"{col} Rank"] = ranks[col].rank(ascending=False, method='min').astype(int)

country_data = ranks[ranks["Country"] == selected_country].iloc[0]

col_deep1, col_deep2 = st.columns(2)

with col_deep1:
    
    def display_metric(title, score_col, raw_label=None, raw_val=None):
        score = country_data[score_col]
        rank = country_data[f"{score_col} Rank"]
        st.markdown(f"**{title}**")
        if raw_label:
            st.markdown(f"🔹 {raw_label}: `{raw_val}` | Score: `{score:.3f}` | Rank: `#{rank}`")
        else:
            st.markdown(f"🔹 Score: `{score:.3f}` | Rank: `#{rank}`")
            
    if w_exp > 0:
        display_metric("1. General Experience", "1. Gen. Exp Score", "Historical Trials", country_data.get("1. Historical Trials (Count)", 0))
    if w_spec_exp > 0:
        display_metric("2. Specific (Gold) Exp", "2. Spec. Exp Score", "Gold Standard Trials", country_data.get("2. Gold Standard Trials (Count)", 0))
    if w_speed > 0:
        display_metric("3. Approval Speed", "3. Speed Score", "Est. Days", country_data.get("3. Est. Approval Time (Days)", 0))
    if w_cost > 0:
        display_metric("4. Cost Efficiency", "4. Cost Score", "Est. Cost ($)", country_data.get("4. Est. Cost per Patient ($)", 0))
    if w_comp > 0:
        display_metric("5. Low Competition", "5. Low Comp. Score", "Active Trials", country_data.get("5. Active Trials (Count)", 0))
        
    st.markdown("---")
    st.markdown(f"🏆 **Final Score:** `{country_data['Final Score']:.3f}` | **Overall Rank: `#{country_data['Rank']}`** | **{country_data['Tier']}**")

with col_deep2:
    radar_categories = []
    if w_exp > 0: radar_categories.append("1. Gen. Exp Score")
    if w_spec_exp > 0: radar_categories.append("2. Spec. Exp Score")
    if w_speed > 0: radar_categories.append("3. Speed Score")
    if w_cost > 0: radar_categories.append("4. Cost Score")
    if w_comp > 0: radar_categories.append("5. Low Comp. Score")

    if radar_categories:
        radar_values = [country_data[cat] for cat in radar_categories]
        # Aby opisy radaru były czytelniejsze (bez słowa "Score"):
        clean_radar_labels = [c.replace(" Score", "") for c in radar_categories]
        df_radar = pd.DataFrame(dict(r=radar_values, theta=clean_radar_labels))

        fig_radar = px.line_polar(
            df_radar, 
            r='r', 
            theta='theta', 
            line_close=True,
            range_r=[0, 1.0],
        )
        fig_radar.update_traces(fill='toself', line_color='#4CAF50')
        fig_radar.update_layout(margin=dict(l=40, r=40, t=30, b=30), height=350)
        
        st.plotly_chart(fig_radar, use_container_width=True)

# ==========================================
# 7. GEOGRAFICZNE MAPY CIEPŁA
# ==========================================
st.markdown("---")
st.subheader("🗺️ Geographical Distribution")

col_map1, col_map2 = st.columns(2)

with col_map1:
    fig_hist = px.choropleth(
        df_metrics,
        locations="Country",
        locationmode="country names",
        color="1. Historical Trials (Count)", # Zaktualizowana nazwa
        hover_name="Country",
        color_continuous_scale="Blues",
        title=f"📚 Historical Experience ({len(hist_studies)} trials)"
    )
    fig_hist.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'))
    st.plotly_chart(fig_hist, use_container_width=True)

with col_map2:
    fig_comp = px.choropleth(
        df_metrics,
        locations="Country",
        locationmode="country names",
        color="5. Active Trials (Count)", # Zaktualizowana nazwa
        hover_name="Country",
        color_continuous_scale="Reds",
        title=f"⚔️ Active Competition ({len(comp_studies)} trials)"
    )
    fig_comp.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'))
    st.plotly_chart(fig_comp, use_container_width=True)


# ==========================================
# 8. PRZEJŚCIE DO ANALIZY AI
# ==========================================
st.markdown("---")
st.subheader("🤖 Next Step: AI Benchmark Analysis & Gold Standards")
st.markdown("Proceed to the AI module to find the most similar historical trials, select your **Gold Standards**, and feed them back into the specific experience algorithm above.")

st.session_state.hist_studies_for_ai = hist_studies

if st.button("Go to AI Benchmark 🚀", type="primary"):
    st.switch_page("views/4_ai_benchmark.py") 