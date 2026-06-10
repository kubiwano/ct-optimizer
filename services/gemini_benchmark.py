import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

def run_ai_benchmark(planned_study, historical_studies):
    if not api_key:
        return "⚠️ **Błąd:** Brak klucza API. Upewnij się, że plik `.env` zawiera zmienną `GEMINI_API_KEY`."
        
    if not historical_studies:
        return "Brak badań historycznych do przeanalizowania."

    studies_to_analyze = historical_studies[:25]
    
    context_trials = ""
    for i, study in enumerate(studies_to_analyze):
        protocol = study.get("protocolSection", {})
        
        nct_id = protocol.get("identificationModule", {}).get("nctId", "Brak ID")
        title = protocol.get("identificationModule", {}).get("briefTitle", "Brak tytułu")
        
        eligibility = protocol.get("eligibilityModule", {})
        criteria = eligibility.get("eligibilityCriteria", "Brak kryteriów")
        
        if len(criteria) > 2000:
            criteria = criteria[:2000] + "... [SKRÓCONO]"
            
        design = protocol.get("designModule", {})
        enrollment = design.get("enrollmentInfo", {}).get("count", "N/A")
        
        context_trials += f"--- BADANIE {i+1} ---\nNCT ID: {nct_id}\nTytuł: {title}\nPacjentów: {enrollment}\nKryteria:\n{criteria}\n\n"

    prompt = f"""
    You are an expert Clinical Data Scientist. 
    Your task is to find the 3 historical trials that are MOST SIMILAR to our planned study, to serve as enrollment benchmarks.

    [PLANNED STUDY PARAMS]
    Title: {planned_study.get('title', '')}
    Indication: {planned_study.get('indication', '')}
    Inclusion Criteria: {planned_study.get('inclusion_criteria', 'None')}
    Exclusion Criteria: {planned_study.get('exclusion_criteria', 'None')}

    [HISTORICAL TRIALS DATA]
    {context_trials}

    [INSTRUCTIONS]
    Analyze the criteria and select the top 3 most similar trials from the historical data.
    Return the result strictly in English as a formatted Markdown text without any conversational fillers:
    
    ### 🥇 [NCT ID] - [Trial Title]
    * **Similarity Score:** [Estimate a % between 0-100]
    * **Enrollment Count:** [Number of patients]
    * **Why it's a good benchmark:** [1-2 precise sentences explaining specifically how the inclusion/exclusion criteria overlap].
    
    (Repeat for 🥈 and 🥉).
    """
    
    try:
        # Pobieramy dynamicznie listę wspieranych modeli
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Preferujemy cokolwiek z rodziny "flash" (szybsze i lżejsze dla limitów)
        target_model = next((m for m in models if "flash" in m.lower()), None)
        
        # Jeśli nie ma flasha, bierzemy pierwszy wspierany model (dzięki przycięciu danych limit 429 nas nie dotyczy)
        if not target_model:
            target_model = models[0] if models else "gemini-pro"
            
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"⚠️ **Błąd API Gemini:** {e}\n\n*(Debug Info - użyto modelu: {target_model})*"