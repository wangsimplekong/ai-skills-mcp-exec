"""
main.py

FastAPI + WebSocket 全链路。
使用 LangChain create_agent + SkillMiddleware + LangGraph streaming。

WSS 完整事件流：
  thinking → (cache_hit?) → skill_loading → skill_loaded
  → tool_start → tool_done（每步）
  → answering → stream_chunk（多次）→ final_result
"""
import uuid
import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from config import settings
from events import EventType, WssEvent
from skill_middleware import SkillMiddleware, reload_skills
from mcp_client import get_mcp_tools
from semantic_cache import init_db, search_cache, write_cache


# ------------------------------------------------------------------ #
# 全局实例                                                              #
# ------------------------------------------------------------------ #

agent       = None
mcp_tools   = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, mcp_tools

    # 初始化数据库（pgvector）
    await init_db()

    # 加载 MCP 工具（从 Nacos 发现 Java MCP 服务）
    mcp_tools = await get_mcp_tools(settings.skills_dir)

    # 初始化 LLM（new api 中转，OpenAI 兼容）
    model = init_chat_model(
        model         = settings.llm_model,
        model_provider = "openai",
        api_key       = settings.llm_api_key,
        base_url      = settings.llm_base_url,
    )

    # 创建 agent：SkillMiddleware 注入 Layer1，load_skill 工具处理 Layer2
    agent = create_agent(
        model,
        system_prompt = (
            "你是企业 AI 助手，专注于水利水务领域的业务数据查询与分析。\n"
            "当用户提问时：\n"
            "1. 先判断是否匹配某个 Skill（根据 Available Skills 列表）\n"
            "2. 匹配到后，用 load_skill 加载完整的业务流程说明\n"
            "3. 严格按照 Skill 中定义的步骤和工具调用顺序执行\n"
            "4. 用清晰的自然语言呈现最终结果"
        ),
        tools       = mcp_tools,               # MCP 工具
        middleware  = [SkillMiddleware()],      # Skills 加载
        checkpointer = InMemorySaver(),         # 会话状态持久化
    )

    skill_count = len(SkillMiddleware._SKILLS if hasattr(SkillMiddleware, '_SKILLS') else [])
    print(f"[启动] 已加载 MCP 工具: {len(mcp_tools)} 个")
    yield


app = FastAPI(lifespan=lifespan)


# ------------------------------------------------------------------ #
# WebSocket 端点                                                        #
# ------------------------------------------------------------------ #

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    await ws.accept()

    async def push(event_type: EventType, data: dict, message_id: str = ""):
        event = WssEvent(
            event      = event_type,
            session_id = session_id,
            message_id = message_id,
            data       = data,
        )
        await ws.send_text(event.model_dump_json())

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            if msg.get("type") != "chat":
                continue

            user_query = msg.get("message", "").strip()
            if not user_query:
                continue

            message_id = f"msg_{uuid.uuid4().hex[:12]}"
            # 每条消息在独立 task 里处理，不阻塞接收
            asyncio.create_task(
                handle_chat(user_query, session_id, message_id, push)
            )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await push(EventType.ERROR, {"message": str(e)})


# ------------------------------------------------------------------ #
# 核心处理链                                                            #
# ------------------------------------------------------------------ #

async def handle_chat(
    user_query: str,
    session_id: str,
    message_id: str,
    push,
):
    await push(EventType.THINKING, {"message": "正在分析意图..."}, message_id)

    # ① 语义缓存查询（意图 → skill_id 映射）
    cached_skills = await search_cache(user_query)
    if cached_skills:
        await push(EventType.CACHE_HIT, {
            "message":  "命中语义缓存",
            "skill_ids": cached_skills,
        }, message_id)

    # ② LangGraph streaming 执行
    config = {
        "configurable": {"thread_id": session_id},
        "run_id": message_id,
    }

    full_content   = ""
    loaded_skills  = []
    active_tools   = {}   # {tool_call_id: tool_name}

    # astream_events 返回 LangGraph 内部所有事件
    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": user_query}]},
        config  = config,
        version = "v2",
    ):
        kind = event.get("event", "")
        name = event.get("name", "")
        data = event.get("data", {})

        # load_skill 工具被调用 → Skill 正在加载
        if kind == "on_tool_start" and name == "load_skill":
            skill_name = data.get("input", {}).get("skill_name", "")
            loaded_skills.append(skill_name)
            await push(EventType.SKILL_LOADING, {
                "skill_name": skill_name,
                "message":    f"正在加载 Skill: {skill_name}",
            }, message_id)

        # load_skill 工具完成 → Skill 加载完成
        elif kind == "on_tool_end" and name == "load_skill":
            skill_name = loaded_skills[-1] if loaded_skills else ""
            await push(EventType.SKILL_LOADED, {
                "skill_name": skill_name,
                "message":    f"Skill 加载完成: {skill_name}",
            }, message_id)

            # 回写语义缓存（异步，不阻塞）
            if loaded_skills:
                asyncio.create_task(
                    write_cache(user_query, loaded_skills)
                )

        # MCP 业务工具开始执行
        elif kind == "on_tool_start" and name not in ("load_skill", "list_skills"):
            tool_call_id = event.get("run_id", "")
            active_tools[tool_call_id] = name
            await push(EventType.TOOL_START, {
                "tool":   name,
                "params": data.get("input", {}),
            }, message_id)

        # MCP 业务工具执行完成
        elif kind == "on_tool_end" and name not in ("load_skill", "list_skills"):
            tool_call_id = event.get("run_id", "")
            active_tools.pop(tool_call_id, None)
            output = data.get("output", "")
            await push(EventType.TOOL_DONE, {
                "tool":   name,
                "result_summary": _summarize(output),
            }, message_id)

        # LLM 开始生成最终回答
        elif kind == "on_chat_model_start" and not active_tools and loaded_skills:
            await push(EventType.ANSWERING, {
                "message": "正在生成回答..."
            }, message_id)

        # 流式文字 chunk
        elif kind == "on_chat_model_stream":
            chunk = data.get("chunk", {})
            delta = ""
            if hasattr(chunk, "content"):
                delta = chunk.content or ""
            elif isinstance(chunk, dict):
                delta = chunk.get("content", "")

            if delta:
                full_content += delta
                await push(EventType.STREAM_CHUNK, {
                    "delta": delta
                }, message_id)

    # ③ 最终结果
    await push(EventType.FINAL_RESULT, {
        "content":       full_content,
        "skills_used":   loaded_skills,
        "session_id":    session_id,
    }, message_id)


def _summarize(output: any) -> str:
    """把工具输出压缩成一行摘要"""
    if isinstance(output, str) and len(output) > 120:
        return output[:120] + "..."
    if isinstance(output, dict):
        return f"返回字段: {', '.join(list(output.keys())[:4])}"
    return str(output)[:120]


# ------------------------------------------------------------------ #
# HTTP 管理接口                                                          #
# ------------------------------------------------------------------ #

@app.get("/skills")
def list_skills_api():
    """查看已加载的 Skills（Layer1 信息）"""
    from skill_middleware import _SKILLS
    return [
        {
            "name":        s["name"],
            "description": s["description"],
            "keywords":    s["keywords"],
        }
        for s in _SKILLS
    ]


@app.post("/skills/reload")
def reload_skills_api():
    """新增/修改 SKILL.md 后热重载"""
    count = reload_skills()
    return {"loaded": count}


@app.get("/health")
def health():
    return {"status": "ok", "mcp_tools": len(mcp_tools)}
