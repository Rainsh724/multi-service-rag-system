from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "retrieval-service"
    app_env: str = "development"

    database_url: str

    embedding_api_url: str = (
        "http://212.80.22.161:8003/v1/embeddings"
    )
    embedding_dimension: int = 768
    embedding_query_prefix: str = "query: "

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()