from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "finvox-verify-2026"
    WHATSAPP_API_VERSION: str = "v21.0"

    DATABASE_URL: str = "sqlite:///./finvox.db"
    FRONTEND_URL: str = "http://localhost:3000"
    DEV_MODE: bool = True

    # Admin token for /api/admin/feedback. Set this in production .env.
    ADMIN_TOKEN: str = "change-me-in-production"


settings = Settings()
