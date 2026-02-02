"""
PartnerCalc OS - WHOIS Lookup
חילוץ פרטי בעל דומיין
"""
import asyncio
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from loguru import logger

# Free WHOIS lookup
try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False
    logger.warning("python-whois not installed. WHOIS lookup disabled.")


class WhoisLookup:
    """
    חיפוש פרטי WHOIS של דומיינים
    """
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}  # Cache results
    
    def extract_domain(self, url: str) -> str:
        """חילוץ דומיין מ-URL"""
        try:
            # If it's already just a domain (no protocol)
            if not url.startswith("http"):
                return url.replace("www.", "")
            
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain if domain else url
        except:
            return url
    
    async def lookup(self, url_or_domain: str) -> Dict[str, Any]:
        """
        חיפוש פרטי WHOIS
        
        Returns:
            {
                "domain": "example.com",
                "registrant_name": "John Doe",
                "registrant_email": "john@example.com",
                "registrant_phone": "+1234567890",
                "registrar": "GoDaddy",
                "creation_date": "2020-01-01",
                "expiration_date": "2025-01-01",
                "is_private": False,
                "error": None
            }
        """
        domain = self.extract_domain(url_or_domain)
        
        # Check cache
        if domain in self.cache:
            logger.debug(f"WHOIS cache hit: {domain}")
            return self.cache[domain]
        
        if not WHOIS_AVAILABLE:
            return {
                "domain": domain,
                "error": "python-whois not installed",
                "is_private": True
            }
        
        try:
            logger.info(f"Starting WHOIS lookup for: {domain}")
            
            # Run in thread pool (whois is blocking)
            loop = asyncio.get_event_loop()
            w = await loop.run_in_executor(None, whois.whois, domain)
            
            logger.info(f"WHOIS raw result for {domain}: {type(w)}")
            
            if w is None:
                return {
                    "domain": domain,
                    "error": "No WHOIS data returned",
                    "is_private": True
                }
            
            result = self._parse_whois(domain, w)
            
            # Cache result
            self.cache[domain] = result
            
            logger.info(f"WHOIS lookup: {domain} -> {result.get('registrant_org', 'N/A')}")
            return result
            
        except Exception as e:
            logger.warning(f"WHOIS lookup failed for {domain}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                "domain": domain,
                "error": str(e),
                "is_private": True
            }
    
    def _parse_whois(self, domain: str, w) -> Dict[str, Any]:
        """פירוש תוצאות WHOIS - כולל כל פרטי הקשר"""
        
        # Check for privacy protection
        privacy_indicators = [
            "privacy", "protect", "proxy", "whoisguard", 
            "domains by proxy", "contact privacy", "withheld",
            "redacted", "data protected", "private registration"
        ]
        
        registrant_name = self._get_first(w.name)
        registrant_org = self._get_first(w.org)
        registrant_email = self._extract_email(w.emails)
        
        # Try to get phone (not always available)
        registrant_phone = None
        if hasattr(w, 'registrant_phone'):
            registrant_phone = self._get_first(w.registrant_phone)
        
        # Address details
        address = self._get_first(getattr(w, 'address', None))
        city = self._get_first(getattr(w, 'city', None))
        state = self._get_first(getattr(w, 'state', None))
        postal_code = self._get_first(getattr(w, 'registrant_postal_code', None))
        country = self._get_first(w.country)
        
        # Check if private
        is_private = False
        name_lower = (registrant_name or "").lower()
        org_lower = (registrant_org or "").lower()
        email_lower = (registrant_email or "").lower()
        
        for indicator in privacy_indicators:
            if indicator in name_lower or indicator in org_lower or indicator in email_lower:
                is_private = True
                break
        
        # Format dates
        creation_date = self._format_date(w.creation_date)
        expiration_date = self._format_date(w.expiration_date)
        updated_date = self._format_date(getattr(w, 'updated_date', None))
        
        return {
            "domain": domain,
            # פרטי בעל הדומיין
            "registrant_name": registrant_name,
            "registrant_org": registrant_org,
            "registrant_email": registrant_email,
            "registrant_phone": registrant_phone,
            # כתובת
            "address": address,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "country": country,
            # פרטי רישום
            "registrar": self._get_first(w.registrar),
            "creation_date": creation_date,
            "expiration_date": expiration_date,
            "updated_date": updated_date,
            "name_servers": w.name_servers[:3] if w.name_servers else [],
            # סטטוס
            "is_private": is_private,
            "error": None
        }
    
    def _get_first(self, value) -> Optional[str]:
        """קבלת ערך ראשון מרשימה או ערך בודד"""
        if value is None:
            return None
        if isinstance(value, list):
            return value[0] if value else None
        return str(value)
    
    def _extract_email(self, emails) -> Optional[str]:
        """חילוץ מייל רלוונטי"""
        if not emails:
            return None
        
        if isinstance(emails, str):
            return emails
        
        if isinstance(emails, list):
            # Filter out abuse/privacy emails
            ignore_patterns = ["abuse", "privacy", "proxy", "whois", "noreply"]
            for email in emails:
                email_lower = email.lower()
                if not any(p in email_lower for p in ignore_patterns):
                    return email
            # Return first if all are filtered
            return emails[0] if emails else None
        
        return None
    
    def _format_date(self, date_val) -> Optional[str]:
        """פורמט תאריך"""
        if date_val is None:
            return None
        
        if isinstance(date_val, list):
            date_val = date_val[0] if date_val else None
        
        if date_val:
            try:
                return date_val.strftime("%Y-%m-%d")
            except:
                return str(date_val)[:10]
        
        return None
    
    async def lookup_batch(self, domains: list, delay: float = 1.0) -> Dict[str, Dict]:
        """
        חיפוש WHOIS למספר דומיינים
        """
        results = {}
        
        for domain in domains:
            result = await self.lookup(domain)
            results[domain] = result
            await asyncio.sleep(delay)  # Rate limiting
        
        return results


# Singleton instance
_whois_lookup: Optional[WhoisLookup] = None

def get_whois_lookup() -> WhoisLookup:
    """קבלת instance של WhoisLookup"""
    global _whois_lookup
    if _whois_lookup is None:
        _whois_lookup = WhoisLookup()
    return _whois_lookup
