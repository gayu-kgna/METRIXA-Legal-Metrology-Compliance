from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator, field_validator
from typing import List, Optional, Any
import os
import json

class Settings(BaseSettings):
    PROJECT_NAME: str = "METRIXA"
    PROJECT_DESCRIPTION: str = "Legal Metrology Inspection Platform"
    LEGAL_FRAMEWORK: str = "Legal Metrology Act, 2009 & Legal Metrology (Packaged Commodities) Rules, 2011"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://metrixa:metrixa_secret_dev_2026@localhost:5432/metrixa_db"
    DB_ECHO: bool = False

    # Security & JWT
    JWT_SECRET_KEY: str = "metrixa_dev_super_secret_jwt_key_sih2026_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Storage Abstraction
    STORAGE_BACKEND: str = "local"
    STORAGE_ROOT: str = "storage"
    MAX_IMAGE_SIZE_MB: int = 15
    MIN_IMAGE_DIMENSION: int = 10
    MAX_IMAGE_DIMENSION: int = 12000
    ALLOWED_IMAGE_FORMATS: List[str] = ["JPEG", "JPG", "PNG", "WEBP"]
    ALLOWED_IMAGE_MIME_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    # OCR Configuration
    TESSERACT_CMD: Optional[str] = None

    # Server & Networking
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Any) -> str:
        """
        Normalize database connection strings to SQLAlchemy asyncpg dialect.
        Handles Supabase, Railway, Neon, and Heroku formats:
        - Converts 'postgres://' or 'postgresql://' to 'postgresql+asyncpg://'
        - Converts 'sslmode=require' query parameter to 'ssl=require' for asyncpg compatibility
        """
        if not v or not isinstance(v, str):
            return v
        url = v.strip()
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        
        # asyncpg does not accept sslmode query parameter; convert to ssl
        if "sslmode=require" in url:
            url = url.replace("sslmode=require", "ssl=require")
        elif "sslmode=disable" in url:
            url = url.replace("sslmode=disable", "")
            url = url.rstrip("?&")
        return url

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """
        Parse CORS allowed origins from either a JSON array string,
        a comma-separated string, or a native list.
        """
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        if isinstance(v, str):
            clean_str = v.strip()
            if clean_str.startswith("[") and clean_str.endswith("]"):
                try:
                    parsed = json.loads(clean_str)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            # Split comma-separated values
            origins = [origin.strip() for origin in clean_str.split(",") if origin.strip()]
            return origins if origins else ["http://localhost:5173"]
        return v

    @model_validator(mode="after")
    def validate_production_hardening(self) -> "Settings":
        if self.ENVIRONMENT.lower() in ("production", "prod"):
            insecure_dev_secrets = [
                "metrixa_dev_super_secret_jwt_key_sih2026_change_in_production",
                "secret",
                "changeme",
                "insecure-default-change-in-production-only"
            ]
            if self.JWT_SECRET_KEY in insecure_dev_secrets or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    "CRITICAL SECURITY FAILURE: Default or insecure JWT_SECRET_KEY cannot be used in production environment. "
                    "Provide a high-entropy secret of at least 32 characters via JWT_SECRET_KEY environment variable."
                )
            if self.DEBUG:
                raise ValueError("CRITICAL SECURITY FAILURE: DEBUG mode must be disabled in production.")
            
            # Unrestricted wildcard CORS check with credentials enabled
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "CRITICAL SECURITY FAILURE: Wildcard '*' in CORS_ORIGINS is prohibited in production when credentials are enabled. "
                    "Specify exact allowed frontend origins (e.g., 'https://metrixa.vercel.app')."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
