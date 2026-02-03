"""
PartnerCalc OS - Scan Campaign Model
מודל סריקות וקמפיינים
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import IntEnum

from app.database import Base


class PipelineStage(IntEnum):
    """Pipeline stages for scan processing"""
    PENDING = 0       # URL collected by Apify
    SCRAPED = 1       # Content scraped by ZenRows
    CLASSIFIED = 2    # GPT analyzed (small_business/bank/etc)
    WHOIS_DONE = 3    # WHOIS lookup completed
    LEAD_CREATED = 4  # Lead created successfully
    FILTERED = 5      # Filtered out (bank/insurance/etc)
    FAILED = 6        # Failed after 3 retries


# Hebrew labels for UI
PIPELINE_STAGE_LABELS = {
    PipelineStage.PENDING: "ממתין",
    PipelineStage.SCRAPED: "תוכן נסרק",
    PipelineStage.CLASSIFIED: "סווג",
    PipelineStage.WHOIS_DONE: "WHOIS נבדק",
    PipelineStage.LEAD_CREATED: "ליד נוצר",
    PipelineStage.FILTERED: "סונן",
    PipelineStage.FAILED: "נכשל",
}


class ScanCampaign(Base):
    """
    טבלת קמפיינים/סריקות - מעקב אחרי סריקות שהורצו
    
    סטטוסים: pending, running, paused, completed, failed
    """
    __tablename__ = "scan_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # פרטי הסריקה
    name = Column(String(255), nullable=False, comment="שם הסריקה")
    keywords = Column(JSON, comment="מילות מפתח לחיפוש")
    category = Column(String(100), comment="קטגוריה")
    results_per_query = Column(Integer, default=100, comment="כמות תוצאות לכל שאילתה")
    
    # סטטיסטיקות
    total_urls = Column(Integer, default=0, comment="כמה URLs נאספו")
    scanned_count = Column(Integer, default=0, comment="כמה נסרקו")
    matched_count = Column(Integer, default=0, comment="כמה נמצאה התאמה")
    discarded_count = Column(Integer, default=0, comment="כמה נפסלו")
    contacted_count = Column(Integer, default=0, comment="כמה נשלחה להם פנייה")
    
    # סטטוס
    status = Column(String(20), default="pending", index=True)
    apify_run_id = Column(String(100), comment="ID של הריצה ב-Apify")
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # AI Analysis Progress
    ai_current_domain = Column(String(255), comment="הדומיין הנוכחי בניתוח AI")
    ai_processed = Column(Integer, default=0, comment="כמה נותחו")
    ai_total = Column(Integer, default=0, comment="סה״כ לניתוח")
    
    # Content Rescan Progress
    rescan_status = Column(String(20), comment="pending, running, completed")
    rescan_processed = Column(Integer, default=0, comment="כמה נסרקו מחדש")
    rescan_total = Column(Integer, default=0, comment="סה״כ לסריקה מחדש")
    
    # ========== Deep Scan Tracking ==========
    deep_scan_status = Column(String(20), comment="pending, running, completed")
    deep_scan_processed = Column(Integer, default=0, comment="כמה אתרים נסרקו בעומק")
    deep_scan_total = Column(Integer, default=0, comment="סה״כ אתרים לסריקה מעמיקה")
    deep_scan_current = Column(String(255), comment="אתר נוכחי בסריקה")
    
    # ========== Calculator Match Tracking ==========
    calc_match_status = Column(String(20), comment="pending, running, completed")
    calc_match_processed = Column(Integer, default=0, comment="כמה אתרים הותאמו")
    calc_match_total = Column(Integer, default=0, comment="סה״כ אתרים להתאמה")
    
    # ========== GPT Calculator Match Tracking ==========
    gpt_match_status = Column(String(20), comment="pending, running, completed")
    gpt_match_processed = Column(Integer, default=0, comment="כמה אתרים הותאמו GPT")
    gpt_match_total = Column(Integer, default=0, comment="סה״כ אתרים להתאמה GPT")
    
    # Relations
    leads = relationship("Lead", back_populates="source_campaign")
    queue_items = relationship("ScanQueue", back_populates="campaign")
    
    def __repr__(self):
        return f"<ScanCampaign(id={self.id}, name='{self.name}', status='{self.status}')>"
    
    @property
    def progress_percent(self) -> float:
        """אחוז התקדמות"""
        if self.total_urls == 0:
            return 0.0
        return (self.scanned_count / self.total_urls) * 100


class ScanQueue(Base):
    """
    טבלת תור סריקות - URLs שממתינים לסריקה
    
    סטטוסים: pending, processing, matched, discarded, contacted, failed
    """
    __tablename__ = "scan_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשר לקמפיין
    campaign_id = Column(Integer, ForeignKey("scan_campaigns.id"), nullable=False, index=True)
    
    # פרטי ה-URL / דומיין
    url = Column(String(500), nullable=False)
    domain = Column(String(255), index=True, comment="דומיין ללא www")
    title = Column(String(500), comment="כותרת מגוגל")
    description = Column(Text, comment="תיאור מגוגל")
    google_position = Column(Integer, comment="מיקום בתוצאות")
    
    # סטטוס
    status = Column(String(20), default="pending", index=True)
    error_message = Column(Text, comment="הודעת שגיאה אם נכשל")
    
    # ========== פרטי קשר מהדף ==========
    emails_found = Column(JSON, comment="מיילים שנמצאו בדף")
    phones_found = Column(JSON, comment="טלפונים שנמצאו בדף")
    contact_form_url = Column(String(500), comment="קישור לטופס יצירת קשר")
    
    # ========== פרטי בעל הדומיין (WHOIS) ==========
    # שדות נפרדים לחיפוש מהיר
    owner_name = Column(String(255), comment="שם בעל הדומיין")
    owner_org = Column(String(255), comment="ארגון/חברה")
    owner_email = Column(String(255), index=True, comment="מייל בעל הדומיין")
    owner_phone = Column(String(50), comment="טלפון בעל הדומיין")
    owner_address = Column(String(500), comment="כתובת")
    owner_city = Column(String(100), comment="עיר")
    owner_country = Column(String(100), comment="מדינה")
    
    # WHOIS מלא כ-JSON (לגיבוי)
    whois_data = Column(JSON, comment="פרטי WHOIS מלאים")
    whois_is_private = Column(Integer, default=0, comment="האם הפרטים מוסתרים")
    
    # תאריכי דומיין
    domain_created = Column(String(20), comment="תאריך רישום הדומיין")
    domain_expires = Column(String(20), comment="תאריך פקיעה")
    registrar = Column(String(255), comment="רשם הדומיין")
    
    # ========== תוכן HTML ==========
    html_body = Column(Text, comment="HTML body של העמוד")
    html_text = Column(Text, comment="טקסט נקי מהעמוד")
    
    # ========== Navigation & Structure ==========
    nav_links = Column(JSON, comment="קישורי תפריט ראשי [{'text': 'אודות', 'href': '/about'}]")
    meta_title = Column(String(500), comment="כותרת מטא")
    meta_description = Column(Text, comment="תיאור מטא")
    meta_keywords = Column(Text, comment="מילות מפתח מטא")
    has_menu_calculator = Column(Integer, default=0, comment="האם יש קישור למחשבון בתפריט")
    
    # ========== ניתוח AI ==========
    business_type = Column(String(50), comment="סוג העסק: private/bank/insurance/corporation/unknown")
    business_type_reason = Column(Text, comment="הסבר AI לסיווג")
    ai_analyzed_at = Column(DateTime(timezone=True), comment="מתי נותח ע״י AI")
    
    # ========== Blacklist ==========
    is_blacklisted = Column(Integer, default=0, comment="האם הדומיין ברשימה שחורה")
    blacklisted_at = Column(DateTime(timezone=True), comment="מתי הוסף לרשימה שחורה")
    
    # ========== Deep Scan ==========
    deep_scan_status = Column(String(20), default="pending", comment="pending, running, completed")
    pages_scanned = Column(Integer, default=0, comment="כמה עמודים נסרקו")
    deep_scan_at = Column(DateTime(timezone=True), comment="מתי בוצעה סריקה מעמיקה")
    
    # ========== Calculator Match ==========
    recommended_calc_id = Column(Integer, ForeignKey("calculators.id"), comment="מחשבון מומלץ ראשי")
    recommended_calc_score = Column(Float, comment="ציון התאמה 0-1")
    recommended_calc_reason = Column(Text, comment="הסבר AI להתאמה")
    all_recommended_calcs = Column(Text, comment="JSON של כל המחשבונים המומלצים")
    calc_matched_at = Column(DateTime(timezone=True), comment="מתי הותאם מחשבון")
    suggested_new_calc = Column(Text, comment="הצעה למחשבון חדש אם אין מתאים")
    
    # ========== GPT Calculator Match ==========
    gpt_recommended_calc_id = Column(Integer, ForeignKey("calculators.id"), comment="מחשבון מומלץ GPT")
    gpt_recommended_calc_score = Column(Float, comment="ציון התאמה GPT 0-1")
    gpt_recommended_calc_reason = Column(Text, comment="הסבר GPT להתאמה")
    gpt_all_recommended_calcs = Column(Text, comment="JSON של כל המחשבונים GPT")
    gpt_matched_at = Column(DateTime(timezone=True), comment="מתי הותאם GPT")
    gpt_match_duration_seconds = Column(Float, comment="כמה שניות לקחה ההתאמה GPT")
    gpt_suggested_new_calc = Column(Text, comment="הצעה GPT למחשבון חדש")
    
    # ========== Pipeline Stage (NEW) ==========
    pipeline_stage = Column(Integer, default=0, index=True, 
                           comment="Pipeline stage: 0=pending, 1=scraped, 2=classified, 3=whois_done, 4=lead_created, 5=filtered, 6=failed")
    retry_count = Column(Integer, default=0, comment="Number of retry attempts (max 3)")
    stage_updated_at = Column(DateTime(timezone=True), comment="When the pipeline stage was last updated")
    
    # ========== תאריכים ==========
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    whois_checked_at = Column(DateTime(timezone=True), comment="מתי נבדק WHOIS")
    contacted_at = Column(DateTime(timezone=True), comment="מתי נשלחה פנייה")
    
    # Relations
    campaign = relationship("ScanCampaign", back_populates="queue_items")
    scanned_pages = relationship("ScannedPage", back_populates="queue_item")
    recommended_calculator = relationship("Calculator", foreign_keys=[recommended_calc_id])
    gpt_recommended_calculator = relationship("Calculator", foreign_keys=[gpt_recommended_calc_id])
    
    def __repr__(self):
        return f"<ScanQueue(id={self.id}, domain='{self.domain}', status='{self.status}')>"
    
    @property
    def best_email(self) -> str:
        """המייל הטוב ביותר ליצירת קשר"""
        # עדיפות: מייל מהדף > מייל WHOIS
        if self.emails_found and len(self.emails_found) > 0:
            return self.emails_found[0]
        if self.owner_email:
            return self.owner_email
        return None
    
    @property
    def best_phone(self) -> str:
        """הטלפון הטוב ביותר ליצירת קשר"""
        if self.phones_found and len(self.phones_found) > 0:
            return self.phones_found[0]
        if self.owner_phone:
            return self.owner_phone
        return None
    
    @property
    def has_contact_info(self) -> bool:
        """האם יש פרטי קשר כלשהם"""
        return bool(
            self.best_email or 
            self.best_phone or 
            self.contact_form_url
        )
    
    @property
    def pipeline_stage_label(self) -> str:
        """Get Hebrew label for current pipeline stage"""
        stage = PipelineStage(self.pipeline_stage or 0)
        return PIPELINE_STAGE_LABELS.get(stage, "לא ידוע")
    
    @property
    def is_pipeline_complete(self) -> bool:
        """Check if pipeline processing is complete (success or filtered or failed)"""
        return self.pipeline_stage in [
            PipelineStage.LEAD_CREATED,
            PipelineStage.FILTERED,
            PipelineStage.FAILED
        ]
    
    @property
    def can_retry(self) -> bool:
        """Check if this item can be retried"""
        return (
            self.pipeline_stage == PipelineStage.FAILED and
            (self.retry_count or 0) < 3
        )