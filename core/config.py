from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Crawl Monitor and Serve Data"
    VERSION: str = "0.1.0"
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "docker"  # Default 'docker'; set 'local' for debugging
    CRAWL_INTERVAL: int = 360  # 6 Hours in minutes
    NOTIFICATIONL_INTERVAL: int = 12
    DB_HOST: str = "db"
    DB_PORT: str = "27017"
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = "crawl_monitor"

    @property
    def DATABASE_URL(self):
        return f"mongodb://{self.DB_HOST}:{self.DB_PORT}"

    @property
    def MONGODB_URL(self):
        return self.DATABASE_URL

    @property
    def DATABASE_NAME(self):
        return self.DB_NAME

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
