from enum import Enum
from typing import Any
from pydantic import BaseModel
from datetime import datetime, timezone


class EventType(str, Enum):
    THINKING      = "thinking"       # 开始分析
    CACHE_HIT     = "cache_hit"      # 语义缓存命中
    SKILL_LOADING = "skill_loading"  # 正在加载 Skill（load_skill 工具被调用）
    SKILL_LOADED  = "skill_loaded"   # Skill 加载完成
    TOOL_START    = "tool_start"     # MCP 工具开始执行
    TOOL_DONE     = "tool_done"      # MCP 工具执行完成
    TOOL_ERROR    = "tool_error"     # MCP 工具执行出错
    ANSWERING     = "answering"      # 开始生成最终回答
    STREAM_CHUNK  = "stream_chunk"   # 流式文字输出
    FINAL_RESULT  = "final_result"   # 完整结果
    ERROR         = "error"          # 系统错误


class WssEvent(BaseModel):
    event:      EventType
    session_id: str
    message_id: str
    timestamp:  str = ""
    data:       Any = None

    def model_post_init(self, __context: Any) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
