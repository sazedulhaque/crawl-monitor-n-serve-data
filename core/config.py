from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Crawl Monitor and Serve Data"
    VERSION: str = "0.1.0"
    JWT_SECRET: str = "your-secret-key"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "docker"  # Default 'docker'; set 'local' for debugging
    CRAWL_INTERVAL: int = 60
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
