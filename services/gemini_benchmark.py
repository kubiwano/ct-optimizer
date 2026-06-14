import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

def run_ai_table_scoring(planned_study, historical_studies, custom_instructions=""):
    if not api_key or not historical_studies:
        return None

    # NOWY LIMIT: Zwiększono analizę do 100 najważniejszych badań
    studies_to_analyze = historical_studies[:100]
    
    context_trials = ""
    for study in studies_to_analyze:
        protocol = study.get("protocolSection", {})
        nct_id = protocol.get("identificationModule", {}).get("nctId", "Brak ID")
        title = protocol.get("identificationModule", {}).get("briefTitle", "Brak tytułu")
        eligibility = protocol.get("eligibilityModule", {})
        criteria = eligibility.get("eligibilityCriteria", "Brak kryteriów")
        
        if len(criteria) > 1000:
            criteria = criteria[:1000] + "... [SKRÓCONO]"
            
        context_trials += f"NCT ID: {nct_id}\nTitle: {title}\nCriteria:\n{criteria}\n\n"

    # Dynamiczny blok z manualnymi instrukcjami użytkownika
    custom_instructions_block = ""
    if custom_instructions.strip():
        custom_instructions_block = f"\n[USER CUSTOM INSTRUCTIONS]\nPAY EXTRA ATTENTION TO THE FOLLOWING USER REQUIREMENT WHEN SCORING:\n{custom_instructions}\n"

    prompt = f"""
    You are an expert Clinical Data Scientist. Analyze the similarity of the historical trials to our planned study based on inclusion/exclusion criteria.
    
    [PLANNED STUDY PARAMS]
    Title: {planned_study.get('title', '')}
    Indication: {planned_study.get('indication', '')}
    Inclusion Criteria: {planned_study.get('inclusion_criteria', 'None')}
    Exclusion Criteria: {planned_study.get('exclusion_criteria', 'None')}

    [HISTORICAL TRIALS DATA]
    {context_trials}
    {custom_instructions_block}
    [INSTRUCTIONS]
    For EACH historical trial provided above, estimate a Similarity Score (0 to 100) and provide a short 1-2 sentence explanation in English of why it matches or differs.
    Return the result strictly as a valid JSON array of objects. Do not wrap it in markdown code blocks. Do not include any other conversational text.
    
    Expected JSON format:
    [
      {{
        "nct_id": "NCT12345678",
        "similarity_score": 85,
        "explanation": "Short explanation in English..."
      }}
    ]
    """
    
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in models if "flash" in m.lower()), None)
        if not target_model:
            target_model = models[0] if models else "gemini-1.5-flash"
            
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt)
        
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()
        
        return json.loads(raw_text)
    except Exception as e:
        print(f"Error in Gemini scoring: {e}")
        return None