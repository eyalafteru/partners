"""
PartnerCalc OS - Configuration
הגדרות המערכת מקובץ .env
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Literal


class Settings(BaseSettings):
    """הגדרות המערכת"""
    
    # ========== Database Type ==========
    # Options: "sqlite", "mysql", "postgresql"
    db_type: Literal["sqlite", "mysql", "postgresql"] = "mysql"
    
    # ========== Database Connection ==========
    db_host: str = "localhost"
    db_port: int = 3306  # MySQL/MariaDB default
    db_user: str = "partnercalc"
    db_password: str = "partnercalc123"
    db_name: str = "partnercalc"
    database_url: Optional[str] = None  # Override full URL if needed
    
    # Legacy PostgreSQL settings (for backward compatibility)
    pg_host: str = "185.151.198.29"
    pg_port: int = 35432
    pg_user: str = "postgresql_ppcmedia"
    pg_password: str = "pwaTaRA8SfHaDDp2"
    pg_name: str = "partnercalc"
    
    # ========== AI - Ollama ==========
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M"
    
    # ========== AI - OpenAI GPT ==========
    openai_api_key: str = ""
    
    # ========== AI - Anthropic Claude ==========
    anthropic_api_key: str = ""
    
    # ========== AI - Default Model ==========
    # Options: "gpt-4o-mini", "gpt-4o", "claude-sonnet-4", "claude-sonnet-4-5"
    default_ai_model: str = "gpt-4o-mini"
    
    # ========== WhatsApp - Green-API ==========
    green_api_instance: str = ""
    green_api_token: str = ""
    
    # ========== Email - SendGrid ==========
    sendgrid_api_key: str = ""
    email_from: str = "noreply@example.com"
    email_from_name: str = "PartnerCalc"
    
    # ========== Email - IMAP (קריאת מיילים נכנסים) ==========
    imap_host: str = "loan-israel.co.il"
    imap_port: int = 993
    imap_user: str = "eyal@loan-israel.co.il"
    imap_password: str = ""
    imap_use_ssl: bool = True
    
    # ========== Email - SMTP (שליחת מיילים) ==========
    smtp_host: str = "loan-israel.co.il"
    smtp_port: int = 465
    smtp_user: str = "eyal@loan-israel.co.il"
    smtp_password: str = ""
    smtp_use_ssl: bool = True
    
    # ========== SMS - Twilio ==========
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    
    # ========== WhatsApp - Green API ==========
    greenapi_url: str = "https://7105.api.greenapi.com"
    greenapi_instance_id: str = ""
    greenapi_api_token: str = ""
    greenapi_notify_phone: str = ""  # Phone number to receive notifications (e.g. 972509543601)
    
    # ========== Scraping - Apify ==========
    apify_token: str = ""  # Set via APIFY_TOKEN env variable
    
    # ========== Apify - Facebook Marketing Actors ==========
    apify_fb_poster_actor: str = "bhansalisoft/facebook-group-auto-poster"
    apify_fb_comments_actor: str = "apify/facebook-comments-scraper"
    apify_fb_messenger_actor: str = "clothefobia/facebook-auto-message-sender"
    apify_fb_groups_scraper: str = "memo23/facebook-search-groups-scraper"
    
    # ========== Facebook - Cookie for Apify Actors ==========
    facebook_cookie: str = ""  # JSON cookie from browser extension
    
    # ========== Facebook - Anti-Spam Settings ==========
    fb_max_posts_per_day: int = 10  # מקסימום פוסטים ליום
    fb_max_posts_per_group_per_week: int = 1  # מקסימום פוסט לקבוצה בשבוע
    fb_min_delay_between_posts: int = 300  # מינימום 5 דקות בין פוסטים (בשניות)
    fb_max_delay_between_posts: int = 900  # מקסימום 15 דקות בין פוסטים (בשניות)
    fb_posting_hours_start: int = 8  # שעת התחלה לפרסום (08:00)
    fb_posting_hours_end: int = 22  # שעת סיום לפרסום (22:00)
    fb_max_replies_per_hour: int = 20  # מקסימום תגובות בשעה
    fb_cooldown_after_block: int = 86400  # המתנה של 24 שעות אחרי חסימה (בשניות)
    
    # ========== Replicate - Image Generation ==========
    replicate_api_token: str = ""  # Set via REPLICATE_API_TOKEN env variable
    replicate_flux_version: str = "091495765fa5ef2725a175a57b276ec30dc9d39c22d30410f2ede68a3eab66b3"
    
    # ========== Proxy ==========
    proxy_service_url: Optional[str] = None
    
    # ========== Security ==========
    encryption_key: str = ""
    jwt_secret: str = ""
    
    # ========== Redis ==========
    redis_url: str = "redis://localhost:6379/0"
    
    # ========== App ==========
    app_env: str = "development"
    debug: bool = True
    
    # ========== Legacy: use_sqlite flag (backward compatibility) ==========
    use_sqlite: bool = False
    
    @property
    def effective_db_type(self) -> str:
        """Get effective database type (considering legacy use_sqlite)"""
        if self.use_sqlite:
            return "sqlite"
        return self.db_type
    
    @property
    def get_database_url(self) -> str:
        """בניית Connection String"""
        # If full URL provided, use it
        if self.database_url:
            return self.database_url
        
        db_type = self.effective_db_type
        
        if db_type == "sqlite":
            return "sqlite:///./partnercalc.db"
        
        elif db_type == "mysql":
            # MySQL/MariaDB with pymysql
            return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        
        elif db_type == "postgresql":
            # PostgreSQL - use legacy pg_* settings if available
            host = self.pg_host if self.pg_host != "185.151.198.29" else self.db_host
            port = self.pg_port if self.pg_port != 35432 else self.db_port
            user = self.pg_user if self.pg_user != "postgresql_ppcmedia" else self.db_user
            password = self.pg_password if self.pg_password != "pwaTaRA8SfHaDDp2" else self.db_password
            name = self.pg_name if self.pg_name != "partnercalc" else self.db_name
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
        
        else:
            raise ValueError(f"Unknown database type: {db_type}")
    
    @property
    def async_database_url(self) -> str:
        """Connection String לחיבור אסינכרוני"""
        db_type = self.effective_db_type
        
        if db_type == "sqlite":
            return "sqlite+aiosqlite:///./partnercalc.db"
        
        elif db_type == "mysql":
            # MySQL/MariaDB with aiomysql
            return f"mysql+aiomysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        
        elif db_type == "postgresql":
            # PostgreSQL with asyncpg
            host = self.pg_host if self.pg_host != "185.151.198.29" else self.db_host
            port = self.pg_port if self.pg_port != 35432 else self.db_port
            user = self.pg_user if self.pg_user != "postgresql_ppcmedia" else self.db_user
            password = self.pg_password if self.pg_password != "pwaTaRA8SfHaDDp2" else self.db_password
            name = self.pg_name if self.pg_name != "partnercalc" else self.db_name
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
        
        else:
            raise ValueError(f"Unknown database type: {db_type}")
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite"""
        return self.effective_db_type == "sqlite"
    
    @property
    def is_mysql(self) -> bool:
        """Check if using MySQL/MariaDB"""
        return self.effective_db_type == "mysql"
    
    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL"""
        return self.effective_db_type == "postgresql"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore unknown env variables


@lru_cache()
def get_settings() -> Settings:
    """קבלת הגדרות (cached)"""
    return Settings()


# ייצוא הגדרות גלובלי
settings = get_settings()
