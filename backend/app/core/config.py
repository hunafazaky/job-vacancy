from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres
    database_url: str = "postgresql+asyncpg://app:changeme@db:5432/job_vacancy_db"

    # Auth
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Vision LLM (free tier)
    gemini_api_key: str = ""
    gemini_vision_model: str = "gemini-2.0-flash"
    groq_api_key: str = ""
    groq_vision_model: str = "llama-3.2-90b-vision-preview"

    # Upload limits
    max_image_size_mb: int = 5
    allowed_image_types: str = "image/jpeg,image/png,image/webp"

    # CORS — comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:5173"

    # Rate limits
    anon_daily_limit: int = 3
    user_daily_limit: int = 5

    # Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "job-vacancy-images"
    r2_public_base_url: str = ""

    @property
    def allowed_image_types_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_image_types.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_image_size_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024


settings = Settings()
