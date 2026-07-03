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
    STRIPE_AGENCY_MONTHLY_PRICE_ID: str = ""
    STRIPE_BILLING_PROVIDER_SEAT_PRICE_ID: str = ""
    STRIPE_ENROLLMENT_TIER_PRICE_ID: str = ""
    STRIPE_PARTNER_ACCOUNT_ID: str = ""
    STRIPE_PARTNER_SHARE: float = 0.35

    # Geocoding (server-side key for ZIP+4 enrichment at PDF generation)
    RADAR_API_KEY: str = ""

    # USPS v3 API — ZIP+4 address verification (register at developers.usps.com)
    USPS_CLIENT_ID: str = ""
    USPS_CLIENT_SECRET: str = ""

    # Resend email
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "DoulaShield <noreply@doulashield.com>"

    # Lead capture
    ADMIN_NOTIFICATION_EMAIL: str = ""  # receives new-lead notifications
    CORS_EXTRA_ORIGINS: str = ""  # comma-separated extra CORS origins (e.g. marketing site)
    SETUP_CALL_URL: str = ""                # Calendly / booking link shown in quiz result emails
    WEBINAR_REGISTER_URL: str = ""          # Individual webinar registration link (quiz results + webinar confirmation)
    WEBINAR_REGISTER_URL_AGENCY: str = ""   # Agency webinar URL; falls back to WEBINAR_REGISTER_URL if empty
    WEBINAR_VIDEO_URL: str = ""             # Pre-recorded individual webinar video link
    WEBINAR_VIDEO_URL_AGENCY: str = ""      # Pre-recorded agency webinar video link; falls back to WEBINAR_VIDEO_URL if empty
    CAL_COM_WEBHOOK_SECRET: str = ""        # HMAC-SHA256 secret from Cal.com Settings → Webhooks

    # Google / Gmail OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GMAIL_SEND_AS: str = ""  # alias From address, e.g. support@doulashield.com

    # Internal ops
    INTERNAL_SECRET: str = ""  # required for POST /internal/trigger-remittance-sync

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
