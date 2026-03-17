"""
semantic_cache.py

pgvector 语义缓存：缓存「用户意图 → skill_id」的映射。
命中缓存后跳过 LLM 路由，直接知道用哪个 skill。
"""
import json
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Float, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy import text

from config import settings


# ------------------------------------------------------------------ #
# DB 模型                                                               #
# ------------------------------------------------------------------ #

class Base(DeclarativeBase):
    pass


class IntentCache(Base):
    __tablename__ = "intent_cache"

    id          = Column(String(64), primary_key=True)
    tenant_id   = Column(String(64), default="default")
    query       = Column(Text, nullable=False)       # 原始用户输入
    embedding   = Column(Vector(1536))               # 查询向量
    skill_ids   = Column(JSONB, nullable=False)      # 匹配到的 skill 列表
    hit_count   = Column(Integer, default=0)
    confidence  = Column(Float, default=1.0)


# ------------------------------------------------------------------ #
# Embedding 客户端                                                       #
# ------------------------------------------------------------------ #

_embed_client = AsyncOpenAI(
    api_key  = settings.llm_api_key,
    base_url = settings.llm_base_url,
)


async def _embed(text: str) -> list[float]:
    resp = await _embed_client.embeddings.create(
        model = settings.embedding_model,
        input = text,
    )
    return resp.data[0].embedding


# ------------------------------------------------------------------ #
# 缓存操作                                                              #
# ------------------------------------------------------------------ #

_engine       = create_async_engine(settings.postgres_dsn)
_SessionLocal = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """建表（首次启动时调用）"""
    async with _engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def search_cache(query: str, tenant_id: str = "default") -> list[str] | None:
    """
    向量检索语义缓存。
    返回命中的 skill_ids 列表，未命中返回 None。
    """
    query_emb = await _embed(query)
    threshold = settings.cache_similarity_threshold

    async with _SessionLocal() as session:
        # pgvector 余弦相似度查询
        result = await session.execute(
            text("""
                SELECT skill_ids, hit_count,
                       1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                FROM intent_cache
                WHERE tenant_id = :tenant_id
                  AND 1 - (embedding <=> CAST(:emb AS vector)) > :threshold
                ORDER BY similarity DESC
                LIMIT 1
            """),
            {
                "emb":       str(query_emb),
                "tenant_id": tenant_id,
                "threshold": threshold,
            }
        )
        row = result.fetchone()
        if not row:
            return None

        # 更新命中次数
        await session.execute(
            text("""
                UPDATE intent_cache
                SET hit_count = hit_count + 1
                WHERE tenant_id = :tenant_id
                  AND 1 - (embedding <=> CAST(:emb AS vector)) > :threshold
            """),
            {"emb": str(query_emb), "tenant_id": tenant_id, "threshold": threshold}
        )
        await session.commit()

        return row.skill_ids


async def write_cache(
    query:     str,
    skill_ids: list[str],
    tenant_id: str = "default",
):
    """
    把意图→skill 映射写入缓存。
    由路由完成后异步调用，不阻塞主流程。
    """
    import uuid
    query_emb = await _embed(query)

    async with _SessionLocal() as session:
        cache = IntentCache(
            id        = uuid.uuid4().hex,
            tenant_id = tenant_id,
            query     = query,
            embedding = query_emb,
            skill_ids = skill_ids,
        )
        session.add(cache)
        await session.commit()
