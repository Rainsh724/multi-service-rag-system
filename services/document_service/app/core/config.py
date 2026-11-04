from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "document-service"
    app_env: str = "development"

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    storage_path: str = "./storage"
    max_file_size_mb: int = 50

    embedding_api_url: str = (
        "http://212.80.22.161:8003/v1/embeddings"
    )
    embedding_dimension: int = 768
    embedding_batch_size: int = 16

    retrieval_service_url: str = "http://127.0.0.1:8002"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()