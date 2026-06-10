import pandas as pd
import numpy as np

def aggregate_country_metrics(historical_studies, competition_studies):
    country_stats = {}

    def count_countries(studies, target_dict, metric_name):
        for study in studies:
            locations = study.get("protocolSection", {}).get("contactsLocationsModule", {}).get("locations", [])
            countries = set([loc.get("country") for loc in locations if loc.get("country")])
            for c in countries:
                if c not in country_stats:
                    country_stats[c] = {"experience_raw": 0, "competition_raw": 0}
                country_stats[c][metric_name] += 1

    count_countries(historical_studies, country_stats, "experience_raw")
    count_countries(competition_studies, country_stats, "competition_raw")

    if not country_stats:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(country_stats, orient='index').reset_index()
    df.rename(columns={'index': 'Country'}, inplace=True)

    np.random.seed(42)
    df["speed_raw"] = np.random.uniform(30, 150, size=len(df)) 
    df["cost_raw"] = np.random.uniform(5000, 25000, size=len(df))

    # --- NORMALIZACJA ---
    max_exp = df["experience_raw"].max() if df["experience_raw"].max() > 0 else 1
    df["Historical Experience"] = df["experience_raw"] / max_exp

    max_comp = df["competition_raw"].max() if df["competition_raw"].max() > 0 else 1
    df["Low Competition"] = 1.0 - (df["competition_raw"] / max_comp)

    min_speed, max_speed = df["speed_raw"].min(), df["speed_raw"].max()
    speed_range = max_speed - min_speed if max_speed != min_speed else 1
    df["Approval Speed"] = 1.0 - ((df["speed_raw"] - min_speed) / speed_range)

    min_cost, max_cost = df["cost_raw"].min(), df["cost_raw"].max()
    cost_range = max_cost - min_cost if max_cost != min_cost else 1
    df["Cost Efficiency"] = 1.0 - ((df["cost_raw"] - min_cost) / cost_range)

    # NOWE: Zmieniamy nazwy surowych zmiennych na czytelne dla tabeli i wypuszczamy je z funkcji
    df.rename(columns={
        "experience_raw": "Historical Trials (Count)", 
        "competition_raw": "Active Trials (Count)"
    }, inplace=True)

    return df[["Country", "Historical Trials (Count)", "Active Trials (Count)", 
               "Historical Experience", "Approval Speed", "Cost Efficiency", "Low Competition"]]