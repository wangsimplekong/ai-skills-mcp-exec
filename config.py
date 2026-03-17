from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM（new api 中转，OpenAI 兼容格式）
    llm_api_key:  str = "sk-G2Mc9L5wlBTzrAxDieOReb6B2pRxVEpfaavoLnu2UTjhVFVG"
    llm_base_url: str = "http://192.168.100.180:18888/v1"
    llm_model:    str = "qwen3.5-plus"

    # Embedding（语义缓存用）
    embedding_model: str = "Qwen/Qwen3-Embedding-8B"

    # Nacos
    nacos_server:    str = "192.168.100.180:8848"
    nacos_namespace: str = "business-server"

    # Skills 目录
    skills_dir: str = "./skills"

    # PostgreSQL（pgvector 语义缓存）
    postgres_dsn: str = "postgresql+asyncpg://admin:admin123@192.168.100.180:5432/postgres"

    # 语义缓存相似度阈值（超过此值命中缓存）
    cache_similarity_threshold: float = 0.92

    class Config:
        env_file = ".env"


settings = Settings()
