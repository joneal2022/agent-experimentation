"""
Simplified configuration management for testing
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Unified settings class"""
    # Database
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="project_management", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Atlassian
    jira_url: str = Field(default="", env="JIRA_URL")
    jira_username: str = Field(default="", env="JIRA_USERNAME") 
    jira_api_token: str = Field(default="", env="JIRA_API_TOKEN")
    
    confluence_url: str = Field(default="", env="CONFLUENCE_URL")
    confluence_username: str = Field(default="", env="CONFLUENCE_USERNAME")
    confluence_api_token: str = Field(default="", env="CONFLUENCE_API_TOKEN")
    
    tempo_api_token: str = Field(default="", env="TEMPO_API_TOKEN")
    
    # OpenAI
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    # App
    app_name: str = Field(default="Project Management Dashboard", env="APP_NAME")
    debug: bool = Field(default=True, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
    
    @property
    def postgres_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


# Global settings instance
settings = Settings()