import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:latest"
    
    # Groq (fallback when Ollama is unavailable)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Database
    database_url: str = "sqlite:///./procureai.db"
    database_url_sqlite: str = "sqlite:///./procureai.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Email
    email_host: str = "imap.gmail.com"
    email_port: int = 993
    email_user: str = ""
    email_password: str = ""
    email_use_ssl: bool = True
    email_poll_interval: int = 30          # seconds between polls
    email_polling_enabled: bool = True     # auto-start polling on boot

    # Slack
    slack_webhook_url: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
