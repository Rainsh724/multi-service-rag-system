from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "rag-service"
    app_env: str = "development"

    retrieval_service_url: str = "http://127.0.0.1:8002"

    llm_api_base_url: str
    llm_api_key: str
    llm_model: str = "edrac-2"

    default_top_k: int = 5
    max_top_k: int = 20

    min_context_similarity: float = 0.65

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()