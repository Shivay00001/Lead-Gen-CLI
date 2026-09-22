import logging
import time
import requests
from typing import List, Dict, Any

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

logger = logging.getLogger(__name__)

class LeadFetcher:
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def fetch_leads(self, keywords: str, title: str, source: str = "github", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches real prospect leads using public OSINT based on the specified source.
        """
        logger.info(f"Searching {source.upper()} OSINT for '{title}' with keywords '{keywords}'...")
        
        leads = []
        
        if source == "github":
            query = f'{title} {keywords} in:readme in:bio'
            url = f"https://api.github.com/search/users?q={query}&per_page={limit}"
            headers = {'User-Agent': 'LeadGenCLI-OSINT-Bot'}
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    for item in response.json().get('items', []):
                        username = item.get('login', '')
                        profile_url = item.get('html_url', '')
                        
                        detail_resp = requests.get(item.get('url'), headers=headers)
                        if detail_resp.status_code == 200:
                            details = detail_resp.json()
                            full_name = details.get('name') or username
                            name_parts = full_name.split(' ')
                            
                            first_name = name_parts[0]
                            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                            
                            company = details.get('company') or "Unknown Company"
                            bio = details.get('bio') or "No bio available."
                            
                            leads.append({
                                "id": str(len(leads) + 1),
                                "first_name": first_name,
                                "last_name": last_name,
                                "title": title,
                                "company": company.strip('@'), 
                                "linkedin_url": profile_url, 
                                "email": details.get('email') or "N/A", 
                                "search_snippet": bio
                            })
                            
                        time.sleep(1.0)
                else:
                    logger.error(f"GitHub API Error: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Failed to fetch from OSINT API: {e}")
                
        elif source in ["linkedin", "twitter"]:
            if not DDGS:
                logger.error("duckduckgo_search is not installed. Use 'pip install duckduckgo-search'.")
                return []
                
            domain = "linkedin.com/in" if source == "linkedin" else "twitter.com"
            query = f'site:{domain} {title} {keywords}'
            
            try:
                with DDGS() as ddgs:
                    results = ddgs.text(query, max_results=limit + 5)
                    for r in results:
                        url = r.get('href', '')
                        snippet = r.get('body', '')
                        title_text = r.get('title', '')
                        
                        if domain in url:
                            parts = [p.strip() for p in title_text.split('-')]
                            name_parts = parts[0].split(' ')
                            first_name = name_parts[0] if len(name_parts) > 0 else "Unknown"
                            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                            
                            company_name = "Unknown Company"
                            if source == "linkedin" and len(parts) >= 3:
                                company_name = parts[2].split('|')[0].strip()
                                
                            leads.append({
                                "id": str(len(leads) + 1),
                                "first_name": first_name,
                                "last_name": last_name,
                                "title": title,
                                "company": company_name,
                                "linkedin_url": url,
                                "email": "N/A", 
                                "search_snippet": snippet
                            })
                            
                        time.sleep(1.5)
                        if len(leads) >= limit:
                            break
            except Exception as e:
                logger.error(f"Search engine rate limit or error encountered: {e}")
        else:
            logger.error(f"Unknown source: {source}. Please use github, linkedin, or twitter.")
            
        return leads
