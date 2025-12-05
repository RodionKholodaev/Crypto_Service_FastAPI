from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Конфигурация приложения из переменных окружения.
    Загружает значения из .env файла автоматически.
    """
    DATABASE_URL: str
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Singleton экземпляр настроек
settings = Settings()
