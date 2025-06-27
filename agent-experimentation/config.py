"""
Configuration management for the Centralized Project Management System
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="project_management", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="password", env="POSTGRES_PASSWORD")
    
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    chromadb_path: str = Field(default="./chromadb", env="CHROMADB_PATH")
    
    @property
    def postgres_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class AtlassianSettings(BaseSettings):
    """Atlassian API configuration"""
    jira_url: str = Field(env="JIRA_URL")
    jira_username: str = Field(env="JIRA_USERNAME")
    jira_api_token: str = Field(env="JIRA_API_TOKEN")
    
    confluence_url: str = Field(env="CONFLUENCE_URL")
    confluence_username: str = Field(env="CONFLUENCE_USERNAME")
    confluence_api_token: str = Field(env="CONFLUENCE_API_TOKEN")
    
    tempo_api_token: str = Field(env="TEMPO_API_TOKEN")


class OpenAISettings(BaseSettings):
    """OpenAI API configuration"""
    api_key: str = Field(env="OPENAI_API_KEY")
    model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    max_tokens: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    temperature: float = Field(default=0.1, env="OPENAI_TEMPERATURE")


class SchedulingSettings(BaseSettings):
    """Scheduling configuration"""
    ingestion_time: str = Field(default="06:00", env="INGESTION_TIME")  # Daily at 6 AM
    timezone: str = Field(default="UTC", env="TIMEZONE")


class AlertSettings(BaseSettings):
    """Alert system configuration"""
    email_smtp_host: str = Field(default="smtp.gmail.com", env="EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(default=587, env="EMAIL_SMTP_PORT")
    email_username: str = Field(env="EMAIL_USERNAME")
    email_password: str = Field(env="EMAIL_PASSWORD")
    email_from: str = Field(env="EMAIL_FROM")
    
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    
    # Alert thresholds
    stalled_ticket_days: int = Field(default=5, env="STALLED_TICKET_DAYS")


class SecuritySettings(BaseSettings):
    """Security configuration"""
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")


class AppSettings(BaseSettings):
    """Main application settings"""
    app_name: str = Field(default="Project Management Dashboard", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8080"], env="CORS_ORIGINS")


class Settings(BaseSettings):
    """Combined settings"""
    database: DatabaseSettings = DatabaseSettings()
    atlassian: AtlassianSettings = AtlassianSettings()
    openai: OpenAISettings = OpenAISettings()
    scheduling: SchedulingSettings = SchedulingSettings()
    alerts: AlertSettings = AlertSettings()
    security: SecuritySettings = SecuritySettings()
    app: AppSettings = AppSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()