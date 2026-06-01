from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Database (direct connection for Alembic)
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Application-layer encryption for Medicaid ID
    FERNET_KEY: str

    # CORS
    FRONTEND_ORIGIN: str

    # OCR / document scanning
    ANTHROPIC_API_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "client-documents"

    # Rate limiting
    RATE_LIMIT_AUTH: str = "10/minute"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Webhook and external service config
    BACKEND_URL: str = "https://your-backend.railway.app"
    ZIPZIGN_WEBHOOK_SECRET: str = ""
    ZIPZIGN_BASE_URL: str = "https://zipzign.com"

    # Stripe billing
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_DEPOSIT_PRICE_ID: str = ""
    STRIPE_MONTHLY_PRICE_ID: str = ""
    STRIPE_PARTNER_ACCOUNT_ID: str = ""
    STRIPE_PARTNER_SHARE: float = 0.35

    # Geocoding (server-side key for ZIP+4 enrichment at PDF generation)
    RADAR_API_KEY: str = ""

    # USPS Web Tools — free ZIP+4 address verification
    # Register at: https://www.usps.com/business/web-tools-apis/
    USPS_USER_ID: str = ""

    # Resend email
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "DoulaShield <noreply@doulashield.com>"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
