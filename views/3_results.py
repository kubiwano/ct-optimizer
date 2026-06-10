import streamlit as st
import pandas as pd
import plotly.express as px

from api.ctgov_client import CTGovClient
from services.data_aggregator import aggregate_country_metrics

st.title("📊 Optimization Results & Ranking")
st.markdown("Analyze the scoring of potential countries based on **live ClinicalTrials.gov data**.")

api_query = st.session_state.get("api_query", {})
if not api_query:
    st.warning("⚠️ No API parameters found. Please go back to '2. API Query & Criteria' and configure your search.")
    st.stop()

# 1. Zwracamy z cache nie tylko zliczenia, ale całe obiekty JSON, aby nakarmić nimi Gemini
@st.cache_data(show_spinner=False)
def fetch_and_process_data(query_params):
    hist_params = query_params["historical"]
    comp_params = query_params["competition"]
    
    hist_studies = CTGovClient.fetch_studies(
        query_name="Historical",
        condition=hist_params["indication"],
        phases=hist_params["phases"],
        sponsor=hist_params["sponsor"],
        statuses=hist_params["status"],
        limit=1000 
    )
    
    comp_studies = CTGovClient.fetch_studies(
        query_name="Competition",
        condition=comp_params["indication"],
        phases=comp_params["phases"],
        sponsor=comp_params["sponsor"],
        statuses=comp_params["status"],
        limit=1000
    )
    
    df_agg = aggregate_country_metrics(hist_studies, comp_studies)
    return df_agg, hist_studies, comp_studies

with st.spinner("🌍 Fetching live data from ClinicalTrials.gov and calculating metrics..."):
    df_metrics, hist_studies, comp_studies = fetch_and_process_data(api_query)

if df_metrics.empty:
    st.error("No locations found for the provided search criteria. Try broadening your search parameters.")
    st.stop()

# 2. Globalne statystyki zapytania
st.markdown("---")
st.subheader("📈 Global API Insights")
col_m1, col_m2 = st.columns(2)
col_m1.metric("📚 Total Historical Studies Analyzed", len(hist_studies))
col_m2.metric("⚔️ Total Active/Competing Studies Found", len(comp_studies))

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

# 5. Interaktywna Tabela Wyników z nowymi kolumnami
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
# 7. NOWOŚĆ: SEKCJA AI BENCHMARKING (GEMINI)
# ==========================================
st.markdown("---")
st.subheader("🤖 AI Benchmark Analysis (Gemini)")
st.markdown("Use Google Gemini to analyze historical study protocols and find the top 3 most similar trials to estimate your enrollment rates.")

if st.button("🔍 Find Benchmark Trials", type="primary"):
    with st.spinner("Gemini is reading protocols and analyzing similarities. This may take up to 20 seconds..."):
        from services.gemini_benchmark import run_ai_benchmark
        
        # Pobranie profilu naszego badania z sesji (Strona 1)
        planned_study = st.session_state.get("study_params", {})
        
        # Wywołanie modelu
        ai_result = run_ai_benchmark(planned_study, hist_studies)
        
        # Renderowanie ładnego Markdowna
        st.success("✅ Analysis Complete!")
        st.markdown(ai_result)