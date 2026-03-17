"""
mcp_client.py

从 Nacos 发现 Java MCP 服务地址，
通过 langchain-mcp-adapters 把工具转成 LangChain Tool 对象。
"""
import time
import nacos
import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import settings


# ------------------------------------------------------------------ #
# Nacos 服务发现                                                        #
# ------------------------------------------------------------------ #

class NacosResolver:
    """从 Nacos 获取 MCP 服务地址，带本地缓存"""

    def __init__(self):
        self._client = nacos.NacosClient(
            server_addresses = settings.nacos_server,
            namespace        = settings.nacos_namespace,
        )
        self._cache: dict[str, tuple[str, float]] = {}
        self._ttl = 30  # 缓存 30 秒

    def resolve(self, service_name: str) -> str:
        cached = self._cache.get(service_name)
        if cached and time.time() < cached[1]:
            return cached[0]

        instance = self._client.get_best_instance(service_name)
        url = f"http://{instance['ip']}:{instance['port']}"
        self._cache[service_name] = (url, time.time() + self._ttl)
        return url


_resolver = NacosResolver()


# ------------------------------------------------------------------ #
# 扫描所有 MCP 服务（从 skill frontmatter 收集）                         #
# ------------------------------------------------------------------ #

def _collect_mcp_servers(skills_dir: str) -> dict[str, dict]:
    """
    扫描所有 SKILL.md，收集 steps 里声明的 mcp_server 列表，
    从 Nacos 解析地址，构建 MultiServerMCPClient 的配置。
    """
    import yaml
    from pathlib import Path

    servers: dict[str, str] = {}  # {service_name: url}

    for skill_md in Path(skills_dir).rglob("SKILL.md"):
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            continue
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        meta = yaml.safe_load(parts[1]) or {}
        for step in meta.get("steps", []):
            svc = step.get("mcp_server", "")
            if svc and svc not in servers:
                try:
                    servers[svc] = _resolver.resolve(svc)
                except Exception as e:
                    print(f"[Nacos] 无法解析 {svc}: {e}")

    # 构建 langchain-mcp-adapters 的配置格式
    return {
        name: {"url": f"{url}/mcp", "transport": "streamable_http"}
        for name, url in servers.items()
    }


# ------------------------------------------------------------------ #
# 获取所有 MCP 工具（供 create_agent 使用）                              #
# ------------------------------------------------------------------ #

async def get_mcp_tools(skills_dir: str) -> list:
    """
    连接所有 MCP server，返回 LangChain Tool 列表。
    在 FastAPI lifespan 里调用一次。
    """
    server_configs = _collect_mcp_servers(skills_dir)

    if not server_configs:
        print("[MCP] 未发现任何 MCP server，跳过工具加载")
        return []

    client = MultiServerMCPClient(server_configs)
    tools  = await client.get_tools()
    print(f"[MCP] 加载了 {len(tools)} 个工具，来自 {len(server_configs)} 个服务")
    return tools
