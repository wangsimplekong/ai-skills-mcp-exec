"""
skill_middleware.py

基于 LangChain 官方 SkillMiddleware 模式实现，适配文件系统 SKILL.md。

Layer1：所有 skill 的 name + description + keywords 常驻 system prompt
Layer2：agent 调用 load_skill 工具时才读完整 SKILL.md（按需加载）
"""
import yaml
from pathlib import Path
from typing import Callable

from langchain.tools import tool
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage

from config import settings


# ------------------------------------------------------------------ #
# Skill 文件扫描                                                        #
# ------------------------------------------------------------------ #

def _scan_skills(skills_dir: str) -> list[dict]:
    """
    扫描 skills 目录，返回所有 skill 的 Layer1 元数据。
    支持任意层级嵌套目录。
    """
    skills = []
    for skill_md in sorted(Path(skills_dir).rglob("SKILL.md")):
        content = skill_md.read_text(encoding="utf-8")
        meta    = _parse_frontmatter(content)
        if not meta:
            continue
        skills.append({
            "name":        meta.get("name", skill_md.parent.name),
            "description": meta.get("description", ""),
            "keywords":    meta.get("keywords", []),
            "path":        str(skill_md),
        })
    return skills


def _parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


# 全局 skill 列表（启动时加载一次）
_SKILLS: list[dict] = _scan_skills(settings.skills_dir)


# ------------------------------------------------------------------ #
# load_skill 工具（Layer2）                                             #
# ------------------------------------------------------------------ #

@tool
def load_skill(skill_name: str) -> str:
    """
    加载指定 skill 的完整内容到当前上下文。

    当你判断用户的问题需要某个具体业务的详细指导时，调用此工具。
    工具会返回该 skill 的完整说明，包括工具定义、执行流程、参数规则等。

    Args:
        skill_name: skill 的名称，必须是 Available Skills 列表中的名称
    """
    for skill in _SKILLS:
        if skill["name"] == skill_name:
            content = Path(skill["path"]).read_text(encoding="utf-8")
            return f"[Skill Loaded: {skill_name}]\n\n{content}"

    available = ", ".join(s["name"] for s in _SKILLS)
    return f"Skill '{skill_name}' 不存在。可用的 Skills：{available}"


@tool
def list_skills() -> str:
    """
    列出所有可用的 Skills 及其描述。
    当你不确定用哪个 skill 时，可以调用此工具查看完整列表。
    """
    lines = ["## 所有可用 Skills\n"]
    for s in _SKILLS:
        kw = "、".join(s["keywords"][:5]) if s["keywords"] else ""
        lines.append(f"### {s['name']}")
        lines.append(f"描述：{s['description']}")
        if kw:
            lines.append(f"关键词：{kw}")
        lines.append("")
    return "\n".join(lines)


def reload_skills():
    """热重载 skill 列表（新增/修改 SKILL.md 后调用）"""
    global _SKILLS
    _SKILLS = _scan_skills(settings.skills_dir)
    return len(_SKILLS)


# ------------------------------------------------------------------ #
# SkillMiddleware                                                       #
# ------------------------------------------------------------------ #

class SkillMiddleware(AgentMiddleware):
    """
    把所有 skill 的 Layer1 描述注入 system prompt。
    agent 看到描述后，按需调用 load_skill 工具加载完整内容。
    """

    # 注册工具，agent 创建时自动可用
    tools = [load_skill, list_skills]

    def __init__(self):
        # 构建 Layer1 prompt（name + description + 前3个关键词）
        lines = ["## Available Skills\n"]
        for skill in _SKILLS:
            kw_str = ""
            if skill["keywords"]:
                kw_str = f"（关键词：{'、'.join(skill['keywords'][:3])}）"
            lines.append(
                f"- **{skill['name']}**: {skill['description']}{kw_str}"
            )
        lines.append(
            "\n当用户问题匹配到某个 skill 时，使用 load_skill 工具加载完整内容后再执行。"
        )
        self._skills_prompt = "\n".join(lines)

    def wrap_model_call(
        self,
        request:  ModelRequest,
        handler:  Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """把 skill 描述追加到 system prompt（Layer1 常驻）"""
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": f"\n\n{self._skills_prompt}"}
        ]
        modified = request.override(
            system_message=SystemMessage(content=new_content)
        )
        return handler(modified)
