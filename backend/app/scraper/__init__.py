"""
PartnerCalc OS - Scraper Layer
שכבת הסריקה - Apify + ZenRows
"""
from app.scraper.zenrows_scraper import ZenRowsScraper, get_zenrows_scraper, get_smart_scraper
from app.scraper.apify_client import ApifyGoogleScraper, get_apify_scraper
from app.scraper.whois_lookup import WhoisLookup, get_whois_lookup

__all__ = [
    'ZenRowsScraper',
    'get_zenrows_scraper', 
    'get_smart_scraper',  # Backward compatibility
    'ApifyGoogleScraper',
    'get_apify_scraper',
    'WhoisLookup',
    'get_whois_lookup',
]