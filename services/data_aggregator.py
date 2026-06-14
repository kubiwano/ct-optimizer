import pandas as pd
import numpy as np

def aggregate_country_metrics(historical_studies, competition_studies, selected_ncts=None):
    if selected_ncts is None:
        selected_ncts = []
        
    country_stats = {}

    def count_countries(studies, metric_name, is_historical=False):
        for study in studies:
            protocol = study.get("protocolSection", {})
            nct_id = protocol.get("identificationModule", {}).get("nctId")
            
            locations = protocol.get("contactsLocationsModule", {}).get("locations", [])
            countries = set([loc.get("country") for loc in locations if loc.get("country")])
            
            for c in countries:
                if c not in country_stats:
                    country_stats[c] = {"experience_raw": 0, "competition_raw": 0, "specific_exp_raw": 0}
                
                country_stats[c][metric_name] += 1
                
                if is_historical and nct_id in selected_ncts:
                    country_stats[c]["specific_exp_raw"] += 1

    count_countries(historical_studies, "experience_raw", is_historical=True)
    count_countries(competition_studies, "competition_raw", is_historical=False)

    if not country_stats:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(country_stats, orient='index').reset_index()
    df.rename(columns={'index': 'Country'}, inplace=True)

    # Generowanie danych dla szybkości i kosztów
    np.random.seed(42)
    df["speed_raw"] = np.random.uniform(30, 150, size=len(df)).astype(int) 
    df["cost_raw"] = np.random.uniform(5000, 25000, size=len(df)).astype(int)

    # --- NORMALIZACJA (WYBIERAMY NAZWY Z NUMERACJĄ) ---
    max_exp = df["experience_raw"].max() if df["experience_raw"].max() > 0 else 1
    df["1. Gen. Exp Score"] = df["experience_raw"] / max_exp
    
    max_spec = df["specific_exp_raw"].max() if df["specific_exp_raw"].max() > 0 else 1
    df["2. Spec. Exp Score"] = df["specific_exp_raw"] / max_spec
    
    min_speed, max_speed = df["speed_raw"].min(), df["speed_raw"].max()
    speed_range = max_speed - min_speed if max_speed != min_speed else 1
    df["3. Speed Score"] = 1.0 - ((df["speed_raw"] - min_speed) / speed_range)

    min_cost, max_cost = df["cost_raw"].min(), df["cost_raw"].max()
    cost_range = max_cost - min_cost if max_cost != min_cost else 1
    df["4. Cost Score"] = 1.0 - ((df["cost_raw"] - min_cost) / cost_range)

    max_comp = df["competition_raw"].max() if df["competition_raw"].max() > 0 else 1
    df["5. Low Comp. Score"] = 1.0 - (df["competition_raw"] / max_comp)

    # --- ZMIANA NAZW ZMIENNYCH SUROWYCH (BY PASOWAŁY DO PAR Z WYNIKAMI) ---
    df.rename(columns={
        "experience_raw": "1. Historical Trials (Count)", 
        "specific_exp_raw": "2. Gold Standard Trials (Count)",
        "speed_raw": "3. Est. Approval Time (Days)",
        "cost_raw": "4. Est. Cost per Patient ($)",
        "competition_raw": "5. Active Trials (Count)"
    }, inplace=True)

    # Wypuszczamy DataFrame z ułożonymi pięknie "parami"
    return df[[
        "Country", 
        "1. Historical Trials (Count)", "1. Gen. Exp Score", 
        "2. Gold Standard Trials (Count)", "2. Spec. Exp Score", 
        "3. Est. Approval Time (Days)", "3. Speed Score", 
        "4. Est. Cost per Patient ($)", "4. Cost Score", 
        "5. Active Trials (Count)", "5. Low Comp. Score"
    ]]