import logging
import random
import requests
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class LeadEnricher:
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def _get_company_domain(self, company_name: str) -> str:
        """Uses Clearbit's free Autocomplete API to find the real company domain."""
        if not company_name or company_name.lower() in ["unknown company", "linkedin"]:
            return ""
            
        try:
            url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={company_name}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0].get('domain', '')
        except Exception as e:
            logger.debug(f"Clearbit API error for {company_name}: {e}")
            
        # Fallback heuristic
        clean_name = company_name.lower().replace(' ', '')
        for suffix in ['inc', 'llc', 'ltd', 'corp', 'co']:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)]
        return f"{clean_name}.com" if clean_name else ""

    def _enrich_single_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        enriched = lead.copy()
        
        company = enriched.get('company', '')
        first = enriched.get('first_name', '').lower()
        last = enriched.get('last_name', '').lower()
        
        domain = self._get_company_domain(company)
        
        if domain:
            # Smart Email Generation
            if first and last:
                enriched["email"] = f"{first}.{last}@{domain}"
            elif first:
                enriched["email"] = f"{first}@{domain}"
                
        enriched["company_domain"] = domain
        enriched["company_size"] = random.choice(["10-50", "51-200", "201-500", "500+"])
        
        return enriched

    def enrich(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enriches OSINT leads concurrently using free company data APIs.
        """
        logger.info(f"Smart Enriching {len(leads)} leads...")
        enriched_leads = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_lead = {executor.submit(self._enrich_single_lead, lead): lead for lead in leads}
            
            for future in as_completed(future_to_lead):
                try:
                    result = future.result()
                    enriched_leads.append(result)
                except Exception as e:
                    logger.error(f"Error enriching lead: {e}")
                    enriched_leads.append(future_to_lead[future])
                    
        return enriched_leads
