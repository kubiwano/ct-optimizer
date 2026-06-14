import requests
import streamlit as st
import logging

class CTGovClient:
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    @staticmethod
    def fetch_studies(query_name: str, condition: str, phases: list, sponsor: str, statuses: list, start_date: str = None, min_primary_completion_date: str = None, limit: int = 1000):
        page_size = min(limit, 1000)
        
        params = {
            "query.cond": condition,
            "filter.overallStatus": ",".join(statuses) if statuses else None,
            "pageSize": page_size,
            "format": "json",
            # NOWOŚĆ: Dodano 'SponsorCollaboratorsModule' do listy pobieranych pól!
            "fields": "IdentificationModule,ConditionsModule,StatusModule,DesignModule,EligibilityModule,ContactsLocationsModule,SponsorCollaboratorsModule"
        }

        params = {k: v for k, v in params.items() if v is not None}

        advanced_terms = []
        if phases and "ALL" not in phases:
            phase_query = " OR ".join(phases)
            advanced_terms.append(f"AREA[Phase]({phase_query})")
            
        if sponsor and sponsor != "ALL":
            advanced_terms.append(f"AREA[LeadSponsorClass]{sponsor}")
            
        if start_date:
            advanced_terms.append(f"AREA[StartDate]RANGE[{start_date}, MAX]")
            
        # Odcięcie po Primary Completion Date
        if min_primary_completion_date:
            advanced_terms.append(f"AREA[PrimaryCompletionDate]RANGE[{min_primary_completion_date}, MAX]")
            
        if advanced_terms:
            params["query.term"] = " AND ".join(advanced_terms)

        studies = []
        
        try:
            while len(studies) < limit:
                response = requests.get(CTGovClient.BASE_URL, params=params, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                batch = data.get("studies", [])
                
                if not batch:
                    break 
                    
                studies.extend(batch)
                
                next_token = data.get("nextPageToken")
                if not next_token or len(studies) >= limit:
                    break 
                    
                params["pageToken"] = next_token
                
            studies = studies[:limit]
            logging.info(f"[{query_name}] Pomyślnie pobrano {len(studies)} badań.")
            return studies
            
        except Exception as e:
            st.error(f"⚠️ [{query_name}] Błąd sieci lub serwera NLM: {e}")
            return studies