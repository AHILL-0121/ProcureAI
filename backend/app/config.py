import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    # Real environment variables win; then backend/.env.local; then backend/.env
    model_config = SettingsConfigDict(env_file=(os.path.join(BACKEND_DIR, ".env"), os.path.join(BACKEND_DIR, ".env.local")),
                                      extra="ignore")

    # App
    app_env: str = "development"            # development | production | test
    app_host: str = "0.0.0.0"
    app_port: int = 8001
    cors_origins: str = "http://localhost:3000"

    # Database: PostgreSQL (Neon). Required, read from DATABASE_URL.
    database_url: str

    # Groq LLM
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"   # empty string disables vision fallback
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: float = 45.0
    llm_startup_check: bool = True         # send one tiny request to the text and vision models when the API starts
    extraction_max_chars: int = 24000

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60 * 12
    admin_email: str = ""                  # bootstrap admin created on first start when no users exist
    admin_password: str = ""

    # Uploads
    upload_dir: str = ""                    # defaults to backend/uploads
    upload_max_bytes: int = 15 * 1024 * 1024
    upload_rate_per_minute: int = 30

    # ERP data: load the bundled sample dataset (backend/data/erp) into an empty database on start.
    # Set false for a real company, which then imports its own data in Settings -> ERP connection.
    erp_sample_data: bool = True

    # Processing
    worker_concurrency: int = 2
    match_include_erp_invoice_history: bool = False   # count ERP invoice history when computing already-billed quantities
    review_confidence_threshold: float = 0.6

    # Default matching tolerances (overridable per vendor in the database)
    tolerance_qty_pct: float = 0.02
    tolerance_price_pct: float = 0.05
    tolerance_price_abs: float = 0.05       # absolute unit-price slack in document currency
    tolerance_total_abs: float = 1.00       # absolute header-total slack in document currency

    # Email intake (IMAP)
    email_host: str = "imap.gmail.com"
    email_port: int = 993
    email_user: str = ""
    email_password: str = ""
    email_use_ssl: bool = True
    email_poll_interval: int = 30
    email_polling_enabled: bool = True

    @field_validator("database_url")
    @classmethod
    def _postgres_only(cls, v: str) -> str:
        v = v.strip().strip('"').strip("'")
        if v.startswith("postgres://"):          # Neon/Heroku style scheme
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql"):
            return v
        if v.startswith("sqlite") and os.environ.get("APP_ENV") == "test":
            return v                              # the automated test suite only
        raise ValueError("DATABASE_URL must be a PostgreSQL (Neon) connection string, "
                         "e.g. postgresql://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # DATABASE_URL comes from the environment


settings = get_settings()
