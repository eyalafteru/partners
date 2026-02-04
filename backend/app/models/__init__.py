"""
PartnerCalc OS - Database Models
כל המודלים של מסד הנתונים
"""
from app.models.calculator import Calculator
from app.models.lead import Lead
from app.models.communication import Communication
from app.models.installation import Installation
from app.models.scan_campaign import ScanCampaign, ScanQueue
from app.models.scanned_page import ScannedPage
from app.models.prompt import Prompt, AILog
from app.models.api_key import ApiKey
from app.models.auto_reply import AutoReply, PendingReply
from app.models.email_template import EmailTemplate
from app.models.reply_scenario import ReplyScenario
from app.models.email_queue import EmailQueue
from app.models.blacklist import Blacklist
from app.models.post_strategy import PostStrategy
from app.models.facebook_marketing import (
    FacebookGroup,
    FacebookPostTemplate,
    FacebookCampaign,
    FacebookPost,
    FacebookReply,
    FacebookConversation,
    FacebookMessage,
)

__all__ = [
    "Calculator",
    "Lead", 
    "Communication",
    "Installation",
    "ScanCampaign",
    "ScanQueue",
    "ScannedPage",
    "Prompt",
    "AILog",
    "ApiKey",
    "AutoReply",
    "PendingReply",
    "EmailTemplate",
    "ReplyScenario",
    "EmailQueue",
    "Blacklist",
    "PostStrategy",
    # Facebook Marketing
    "FacebookGroup",
    "FacebookPostTemplate",
    "FacebookCampaign",
    "FacebookPost",
    "FacebookReply",
    "FacebookConversation",
    "FacebookMessage",
]
