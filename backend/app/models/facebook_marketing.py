"""
PartnerCalc OS - Facebook Marketing Models
מודלים לניהול פרסום בקבוצות פייסבוק
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from typing import Optional

from app.database import Base


class FacebookGroup(Base):
    """קבוצות פייסבוק לפרסום"""
    __tablename__ = "facebook_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # מזהה הקבוצה בפייסבוק
    fb_group_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500))
    description = Column(Text)
    
    # מטא-דאטא
    member_count = Column(Integer, default=0)
    is_admin = Column(Boolean, default=False)
    group_image_url = Column(String(500))
    category = Column(String(100))  # קטגוריה (עסקים, נדל"ן, הלוואות...)
    tags = Column(JSON, default=[])
    
    # הגדרות
    is_active = Column(Boolean, default=True)
    auto_reply_enabled = Column(Boolean, default=True)
    posting_delay_minutes = Column(Integer, default=30)  # השהייה בין פוסטים
    
    # סטטיסטיקות
    total_posts = Column(Integer, default=0)
    total_replies_received = Column(Integer, default=0)
    total_conversations = Column(Integer, default=0)
    
    # תאריכים
    last_post_at = Column(DateTime(timezone=True))
    synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    posts = relationship("FacebookPost", back_populates="group")
    
    def __repr__(self):
        return f"<FacebookGroup(id={self.id}, name='{self.name}')>"


class FacebookPostTemplate(Base):
    """תבניות לפוסטים"""
    __tablename__ = "facebook_post_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # תוכן התבנית
    base_content = Column(Text, nullable=False)
    
    # משתנים בתבנית: {group_name}, {date}, {link} וכו'
    variables = Column(JSON, default=[])
    
    # הגדרות תמונה
    include_image = Column(Boolean, default=True)
    image_prompt_template = Column(Text)  # תבנית ל-prompt של תמונה
    
    # קטגוריה
    category = Column(String(50))
    
    # סטטיסטיקות
    times_used = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<FacebookPostTemplate(id={self.id}, name='{self.name}')>"


class FacebookCampaign(Base):
    """קמפיינים לפרסום"""
    __tablename__ = "facebook_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # נושא הקמפיין
    topic = Column(String(200), nullable=False)  # למשל: "מחשבונים להטמעה בחינם"
    target_audience = Column(String(200))
    
    # קשר לתבנית
    template_id = Column(Integer, ForeignKey("facebook_post_templates.id"), nullable=True)
    
    # === שדות חדשים - קישור למחשבון ===
    calculator_id = Column(Integer, ForeignKey("calculators.id"), nullable=True)
    calculator_mode = Column(String(20), default="all")  # specific, all, category
    calculator_category = Column(String(100), nullable=True)
    
    # === שדות חדשים - אסטרטגיות ===
    strategy_ids = Column(JSON, default=[])  # JSON array of strategy IDs
    
    # === שדות חדשים - הגדרות קישור ===
    link_placement = Column(String(20), default="in_post")  # in_post, first_comment, none
    
    # === שדות חדשים - Auto-Responder ===
    auto_responder_enabled = Column(Boolean, default=False)
    auto_responder_type = Column(String(20), default="comment")  # comment, messenger, ai_decide
    auto_responder_template = Column(Text, nullable=True)
    auto_responder_delay_minutes = Column(Integer, default=5)
    auto_responder_daily_limit = Column(Integer, default=50)
    
    # הגדרות
    image_percentage = Column(Integer, default=50)  # אחוז פוסטים עם תמונה
    delay_between_posts = Column(Integer, default=60)  # דקות בין פוסטים
    max_posts_per_day = Column(Integer, default=10)
    
    # קבוצות יעד (JSON array of group IDs)
    target_group_ids = Column(JSON, default=[])
    
    # סטטוס: draft, generating, ready, publishing, completed, paused
    status = Column(String(20), default="draft")
    
    # סטטיסטיקות
    total_posts_generated = Column(Integer, default=0)
    total_posts_approved = Column(Integer, default=0)
    total_posts_published = Column(Integer, default=0)
    total_replies = Column(Integer, default=0)
    total_conversations = Column(Integer, default=0)
    
    # תאריכים
    scheduled_start = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    template = relationship("FacebookPostTemplate")
    posts = relationship("FacebookPost", back_populates="campaign")
    
    def __repr__(self):
        return f"<FacebookCampaign(id={self.id}, name='{self.name}', status='{self.status}')>"


class FacebookPost(Base):
    """פוסטים שנוצרו/פורסמו"""
    __tablename__ = "facebook_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשרים
    campaign_id = Column(Integer, ForeignKey("facebook_campaigns.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("facebook_groups.id"), nullable=False)
    
    # === שדות חדשים - קישור למחשבון ואסטרטגיה ===
    calculator_id = Column(Integer, ForeignKey("calculators.id"), nullable=True)
    strategy_id = Column(Integer, ForeignKey("post_strategies.id"), nullable=True)
    
    # === שדות חדשים - תגובה ראשונה ===
    first_comment_content = Column(Text, nullable=True)
    first_comment_posted = Column(Boolean, default=False)
    
    # === שדות חדשים - Auto-Responder ===
    auto_replies_sent = Column(Integer, default=0)
    
    # מזהה בפייסבוק (אחרי פרסום)
    fb_post_id = Column(String(100), unique=True, nullable=True, index=True)
    fb_post_url = Column(String(500))
    
    # תוכן
    content = Column(Text, nullable=False)
    
    # תמונה
    has_image = Column(Boolean, default=False)
    image_prompt = Column(Text)  # ה-prompt שנשלח ל-Replicate
    image_url = Column(String(500))  # URL של התמונה שנוצרה
    
    # סטטוס: draft, pending_approval, approved, publishing, published, failed, rejected
    status = Column(String(20), default="draft")
    rejection_reason = Column(Text)
    
    # Apify
    apify_run_id = Column(String(100))
    publish_error = Column(Text)
    
    # סטטיסטיקות
    replies_count = Column(Integer, default=0)
    messenger_conversations = Column(Integer, default=0)
    
    # תאריכים
    approved_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    campaign = relationship("FacebookCampaign", back_populates="posts")
    group = relationship("FacebookGroup", back_populates="posts")
    replies = relationship("FacebookReply", back_populates="post")
    
    def __repr__(self):
        return f"<FacebookPost(id={self.id}, status='{self.status}')>"


class FacebookReply(Base):
    """תגובות שהתקבלו לפוסטים"""
    __tablename__ = "facebook_replies"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשר לפוסט
    post_id = Column(Integer, ForeignKey("facebook_posts.id"), nullable=False)
    
    # מזהי פייסבוק
    fb_comment_id = Column(String(100), unique=True, index=True)
    fb_user_id = Column(String(100), index=True)
    fb_user_name = Column(String(255))
    fb_user_profile_url = Column(String(500))
    fb_user_profile_pic = Column(String(500))
    
    # תוכן התגובה
    message = Column(Text)
    
    # ניתוח AI
    ai_detected_intent = Column(String(50))  # interested, question, private_request, spam, other
    ai_intent_confidence = Column(Float)
    wants_private = Column(Boolean, default=False)  # האם ביקש "שלח בפרטי"
    ai_analysis = Column(JSON)  # ניתוח מפורט
    
    # סטטוס טיפול: new, pending_response, ai_suggested, approved, responded, ignored
    status = Column(String(20), default="new")
    
    # תגובה מוצעת
    suggested_response = Column(Text)
    suggested_channel = Column(String(20))  # comment, messenger
    
    # תגובה שנשלחה
    actual_response = Column(Text)
    response_channel = Column(String(20))
    responded_at = Column(DateTime(timezone=True))
    
    # תאריכים
    received_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    post = relationship("FacebookPost", back_populates="replies")
    conversation = relationship("FacebookConversation", back_populates="initial_reply", uselist=False)
    
    def __repr__(self):
        return f"<FacebookReply(id={self.id}, user='{self.fb_user_name}', status='{self.status}')>"


class FacebookConversation(Base):
    """שיחות עם מגיבים (תגובות + מסנג'ר)"""
    __tablename__ = "facebook_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשר לתגובה המקורית
    initial_reply_id = Column(Integer, ForeignKey("facebook_replies.id"), nullable=True)
    
    # פרטי המשתמש
    fb_user_id = Column(String(100), nullable=False, index=True)
    fb_user_name = Column(String(255))
    fb_user_profile_url = Column(String(500))
    
    # ערוץ נוכחי: comment, messenger
    current_channel = Column(String(20), default="comment")
    
    # סטטוס: active, ai_handling, human_required, closed, converted
    status = Column(String(20), default="active")
    
    # AI context - היסטוריית השיחה לבוט (JSON)
    ai_context = Column(JSON, default=[])
    
    # האם הפך לליד
    converted_to_lead = Column(Boolean, default=False)
    lead_id = Column(Integer, nullable=True)  # קשר ללידים במערכת
    
    # סטטיסטיקות
    messages_count = Column(Integer, default=0)
    ai_responses_count = Column(Integer, default=0)
    human_responses_count = Column(Integer, default=0)
    
    # תאריכים
    last_message_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    initial_reply = relationship("FacebookReply", back_populates="conversation")
    messages = relationship("FacebookMessage", back_populates="conversation", order_by="FacebookMessage.created_at")
    
    def __repr__(self):
        return f"<FacebookConversation(id={self.id}, user='{self.fb_user_name}', status='{self.status}')>"


class FacebookMessage(Base):
    """הודעות בשיחה (תגובות + מסנג'ר)"""
    __tablename__ = "facebook_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשר לשיחה
    conversation_id = Column(Integer, ForeignKey("facebook_conversations.id"), nullable=False)
    
    # כיוון: inbound (מהלקוח), outbound (מאיתנו)
    direction = Column(String(10), nullable=False)
    
    # ערוץ: comment, messenger
    channel = Column(String(20), nullable=False)
    
    # תוכן
    content = Column(Text, nullable=False)
    
    # מי יצר: ai, human
    created_by = Column(String(10))
    
    # אם outbound - האם אושר לשליחה
    is_approved = Column(Boolean, default=False)
    approved_at = Column(DateTime(timezone=True))
    
    # האם נשלח בפועל
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    send_error = Column(Text)
    
    # מזהי פייסבוק
    fb_message_id = Column(String(100))
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    conversation = relationship("FacebookConversation", back_populates="messages")
    
    def __repr__(self):
        return f"<FacebookMessage(id={self.id}, direction='{self.direction}', channel='{self.channel}')>"
