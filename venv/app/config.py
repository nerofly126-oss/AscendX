from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    DB_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Mail
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # Facebook OAuth
    FACEBOOK_CLIENT_ID: str
    FACEBOOK_CLIENT_SECRET: str

    # Apple OAuth
    APPLE_CLIENT_ID: str
    APPLE_TEAM_ID: str
    APPLE_KEY_ID: str
    APPLE_PRIVATE_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
