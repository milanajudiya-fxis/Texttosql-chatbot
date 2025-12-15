"""Configuration settings for the Text-to-SQL agent"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database configuration"""
    user: str
    password: str
    host: str
    port: int
    db_name: str

    @property
    def uri(self) -> str:
        """Generate database URI"""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"


@dataclass
class LLMConfig:
    """LLM configuration"""
    model: str
    temperature: float
    max_tokens: Optional[int]
    timeout: Optional[float]
    max_retries: int
    api_key: str
    reasoning_effort: str = None   
    max_reasoning_tokens: int = None


@dataclass
class TwilioConfig:
    """Twilio configuration"""
    account_sid: str
    auth_token: str
    from_number: str


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str
    port: int
    db: int
    password: Optional[str] = None
    
    @property
    def url(self) -> str:
        """Generate Redis URL"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class Settings:
    """Application settings"""
    database: DatabaseConfig
    llm: LLMConfig
    twilio: TwilioConfig
    redis: RedisConfig
    debug: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables"""
        db_config = DatabaseConfig(
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "root"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            db_name=os.getenv("DB_NAME", "TextToSQL"),
        )

        llm_config = LLMConfig(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
            max_tokens=None,
            timeout=None,
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            reasoning_effort = os.getenv("LLM_REASONING_EFFORT", "low"),
            max_reasoning_tokens= int(os.getenv("LLM_MAX_REASONING_TOKENS", "0"))
            )
            
        twilio_config = TwilioConfig(
            account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            from_number=os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"),
        )

        redis_config = RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD", None),
        )

        return cls(
            database=db_config,
            llm=llm_config,
            twilio=twilio_config,
            redis=redis_config,
            debug=os.getenv("DEBUG", "False").lower() == "true",
        )
