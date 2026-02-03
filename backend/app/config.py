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
    
    # ========== Scraping - Apify ==========
    apify_token: str = ""  # Set via APIFY_TOKEN env variable
    
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
