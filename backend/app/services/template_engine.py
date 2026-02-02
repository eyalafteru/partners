"""
PartnerCalc OS - Template Engine
מנוע תבניות לעיבוד משתנים
"""
from typing import Dict, Any, Optional
from datetime import datetime
import re
from loguru import logger


# Hebrew month names
HEBREW_MONTHS = {
    1: "ינואר",
    2: "פברואר", 
    3: "מרץ",
    4: "אפריל",
    5: "מאי",
    6: "יוני",
    7: "יולי",
    8: "אוגוסט",
    9: "ספטמבר",
    10: "אוקטובר",
    11: "נובמבר",
    12: "דצמבר"
}

HEBREW_DAYS = {
    0: "שני",
    1: "שלישי",
    2: "רביעי",
    3: "חמישי",
    4: "שישי",
    5: "שבת",
    6: "ראשון"
}


def get_date_variables() -> Dict[str, str]:
    """
    קבלת משתני תאריך
    """
    now = datetime.now()
    
    return {
        "today": f"{now.day} ב{HEBREW_MONTHS[now.month]} {now.year}",
        "today_short": now.strftime("%d/%m/%Y"),
        "current_month": HEBREW_MONTHS[now.month],
        "current_year": str(now.year),
        "day_of_week": HEBREW_DAYS[now.weekday()]
    }


def get_sender_variables() -> Dict[str, str]:
    """
    קבלת משתני שולח מהגדרות
    """
    from app.config import settings
    
    return {
        "my_name": settings.email_from_name or "אייל",
        "my_email": settings.email_from or "eyal@loan-israel.co.il",
        "my_phone": "",  # TODO: add to settings
        "my_company": "הלוואות ישראל",
        "my_title": "מנהל שותפויות",
        "my_signature": f"{settings.email_from_name} | הלוואות ישראל"
    }


def get_lead_variables(lead, campaign=None) -> Dict[str, str]:
    """
    קבלת משתנים מאובייקט ליד
    """
    if not lead:
        return {}
    
    contact_info = lead.contact_info or {}
    
    # Extract contact name - prefer owner_name from scan, fallback to whois
    contact_name = ""
    if hasattr(lead, 'owner_name') and lead.owner_name:
        contact_name = lead.owner_name
    elif contact_info.get("whois_name"):
        contact_name = contact_info.get("whois_name", "")
    
    # Fallback if no name or name is private/hidden
    if not contact_name or "private" in contact_name.lower() or "registration" in contact_name.lower():
        contact_name = "צוות האתר"
    
    contact_first_name = contact_name.split()[0] if contact_name else ""
    
    # Extract email
    contact_email = ""
    if hasattr(lead, 'owner_email') and lead.owner_email:
        contact_email = lead.owner_email
    elif contact_info.get("whois_email"):
        contact_email = contact_info.get("whois_email", "")
    if not contact_email:
        emails = contact_info.get("emails", [])
        if emails:
            contact_email = emails[0]
    
    # Extract phone
    contact_phone = ""
    if hasattr(lead, 'owner_phone') and lead.owner_phone:
        contact_phone = lead.owner_phone
    elif contact_info.get("whois_phone"):
        contact_phone = contact_info.get("whois_phone", "")
    if not contact_phone:
        phones = contact_info.get("phones", [])
        if phones:
            contact_phone = phones[0]
    
    # Get category from campaign keywords (search query)
    category = ""
    if campaign and hasattr(campaign, 'keywords') and campaign.keywords:
        import json
        try:
            keywords = campaign.keywords if isinstance(campaign.keywords, list) else json.loads(campaign.keywords)
            if keywords:
                category = keywords[0]  # First search keyword
        except:
            category = campaign.name or ""
    elif hasattr(lead, 'category') and lead.category:
        category = lead.category
    
    return {
        "domain": lead.domain or "",
        "site_name": lead.site_name or lead.domain or "",
        "site_url": f"https://{lead.domain}" if lead.domain else "",
        "category": category,
        "contact_name": contact_name,
        "contact_first_name": contact_first_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "contact_company": contact_info.get("whois_org", "") or (lead.owner_org if hasattr(lead, 'owner_org') else "")
    }


def get_calculator_variables(calculator, match_info: Dict = None) -> Dict[str, str]:
    """
    קבלת משתנים מאובייקט מחשבון
    """
    if not calculator:
        return {}
    
    match_info = match_info or {}
    
    # Use available fields from Calculator model
    description = ""
    if hasattr(calculator, 'intent_description') and calculator.intent_description:
        description = calculator.intent_description
    elif hasattr(calculator, 'ai_summary') and calculator.ai_summary:
        description = calculator.ai_summary
    
    return {
        "calculator_name": calculator.name or "",
        "calculator_description": description,
        "calculator_benefit": "מגדיל המרות באתר",
        "calculator_demo_url": calculator.target_url or "" if hasattr(calculator, 'target_url') else "",
        "match_score": f"{match_info.get('score', 0)}%",
        "match_reason": match_info.get("reason", ""),
        "all_calculators": ", ".join(match_info.get("all_names", [calculator.name])) if calculator else "",
        "calc_name": calculator.name or ""  # Alias for backward compatibility
    }


def render_template(template: str, variables: Dict[str, Any]) -> str:
    """
    עיבוד תבנית והחלפת משתנים
    
    Supports:
    - {{variable}} - simple replacement
    - {{#if variable}}content{{/if}} - conditional blocks
    - {{fallback:variable:default}} - fallback values
    
    Args:
        template: תבנית עם משתנים
        variables: מילון משתנים
    
    Returns:
        תבנית מעובדת
    """
    if not template:
        return ""
    
    result = template
    
    # 1. Process conditional blocks: {{#if variable}}content{{/if}}
    def replace_conditional(match):
        var_name = match.group(1)
        content = match.group(2)
        
        value = variables.get(var_name, "")
        if value and str(value).strip():
            # Variable has value - show content
            return content
        else:
            # No value - hide content
            return ""
    
    conditional_pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}'
    result = re.sub(conditional_pattern, replace_conditional, result, flags=re.DOTALL)
    
    # 2. Process fallback values: {{fallback:variable:default}}
    def replace_fallback(match):
        var_name = match.group(1)
        default_value = match.group(2)
        
        value = variables.get(var_name, "")
        if value and str(value).strip():
            return str(value)
        else:
            return default_value
    
    fallback_pattern = r'\{\{fallback:(\w+):([^}]+)\}\}'
    result = re.sub(fallback_pattern, replace_fallback, result)
    
    # 3. Process simple variables: {{variable}}
    def replace_simple(match):
        var_name = match.group(1)
        value = variables.get(var_name, "")
        return str(value) if value else ""
    
    simple_pattern = r'\{\{(\w+)\}\}'
    result = re.sub(simple_pattern, replace_simple, result)
    
    return result


def prepare_email_variables(
    lead = None, 
    calculator = None, 
    match_info: Dict = None,
    custom_vars: Dict = None,
    campaign = None
) -> Dict[str, str]:
    """
    הכנת כל המשתנים לשליחת מייל
    
    Args:
        lead: אובייקט ליד
        calculator: אובייקט מחשבון
        match_info: מידע על ההתאמה
        custom_vars: משתנים מותאמים אישית
        campaign: אובייקט קמפיין (לקבלת מילות החיפוש)
    
    Returns:
        מילון עם כל המשתנים
    """
    variables = {}
    
    # Add date variables
    variables.update(get_date_variables())
    
    # Add sender variables
    variables.update(get_sender_variables())
    
    # Add lead variables
    if lead:
        variables.update(get_lead_variables(lead, campaign))
    
    # Add calculator variables
    if calculator:
        variables.update(get_calculator_variables(calculator, match_info))
    
    # Override with custom variables
    if custom_vars:
        variables.update(custom_vars)
    
    return variables


async def render_template_for_lead(
    template_obj,
    lead,
    calculator = None,
    session = None,
    campaign = None
) -> Dict[str, str]:
    """
    עיבוד תבנית עבור ליד ספציפי
    
    Returns:
        {
            "subject": "נושא מעובד",
            "body_text": "גוף טקסט",
            "body_html": "גוף HTML"
        }
    """
    # Prepare variables
    match_info = {}
    
    # Get match info from lead if available
    if lead and hasattr(lead, 'recommended_calc_score'):
        match_info = {
            "score": lead.recommended_calc_score,
            "reason": lead.recommended_calc_reason or ""
        }
    
    # Try to get campaign from lead if not provided
    if not campaign and session and lead:
        from app.models import ScanCampaign, ScanQueue
        from sqlalchemy import select
        
        # First try source_campaign_id
        if hasattr(lead, 'source_campaign_id') and lead.source_campaign_id:
            result = await session.execute(select(ScanCampaign).where(ScanCampaign.id == lead.source_campaign_id))
            campaign = result.scalar_one_or_none()
        
        # Fallback: look up campaign via scan_queue by domain
        if not campaign and hasattr(lead, 'domain') and lead.domain:
            result = await session.execute(
                select(ScanCampaign)
                .join(ScanQueue, ScanQueue.campaign_id == ScanCampaign.id)
                .where(ScanQueue.domain == lead.domain)
                .limit(1)
            )
            campaign = result.scalar_one_or_none()
    
    variables = prepare_email_variables(
        lead=lead,
        calculator=calculator,
        match_info=match_info,
        campaign=campaign
    )
    
    return {
        "subject": render_template(template_obj.subject, variables),
        "body_text": render_template(template_obj.body_text, variables),
        "body_html": render_template(template_obj.body_html, variables) if template_obj.body_html else None
    }
