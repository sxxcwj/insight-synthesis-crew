"""读取实际模型配置，并探测 DeepSeek 与搜索引擎是否已配置、能否连通。"""

import os
import re
import urllib.error
import urllib.request
from pathlib import Path


_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "agents.yaml"
_DEFAULT_MODEL = "deepseek/deepseek-flash"


def display_model_name(model: str) -> str:
    model = (model or "").strip()
    if not model:
        return "未配置"
    if "/" in model:
        return model.split("/", 1)[1]
    return model


def _yaml_llm(agent_name: str) -> str:
    if not _CONFIG_PATH.is_file():
        return ""
    text = _CONFIG_PATH.read_text(encoding="utf-8")
    pattern = rf"(?m)^{re.escape(agent_name)}:\s*$([\s\S]*?)(?=^[^\s#]|\Z)"
    matched = re.search(pattern, text)
    if not matched:
        return ""
    llm = re.search(r"(?m)^\s*llm:\s*(\S+)", matched.group(1))
    return llm.group(1).strip() if llm else ""


def resolve_models() -> tuple[str, str]:
    scout = os.getenv("SCOUT_LLM_MODEL", "").strip() or _yaml_llm("scout_researcher") or _DEFAULT_MODEL
    analyst = os.getenv("ANALYST_LLM_MODEL", "").strip() or _yaml_llm("synthesis_analyst") or scout
    return scout, analyst


def _endpoint_reachable(url: str, headers: dict[str, str], timeout: float) -> bool:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(128)
            return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def probe_deepseek_reachable(api_key: str, timeout: float = 2.5) -> bool:
    return _endpoint_reachable(
        "https://api.deepseek.com/models",
        {"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        timeout,
    )


def probe_serper_reachable(api_key: str, timeout: float = 2.5) -> bool:
    return _endpoint_reachable(
        "https://google.serper.dev",
        {"X-API-KEY": api_key, "Accept": "application/json"},
        timeout,
    )


def _level(configured: bool, reachable: bool | None) -> str:
    if not configured:
        return "red"
    if reachable:
        return "green"
    return "yellow"


def build_runtime_status() -> dict:
    from craw.access_auth import auth_required
    from craw.redact import redaction_enabled

    scout, analyst = resolve_models()
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    serper_key = os.getenv("SERPER_API_KEY", "").strip()
    deepseek_reachable = probe_deepseek_reachable(deepseek_key) if deepseek_key else None
    serper_reachable = probe_serper_reachable(serper_key) if serper_key else None
    return {
        "model": scout,
        "model_label": display_model_name(scout),
        "scout_model": scout,
        "analyst_model": analyst,
        "deepseek": {
            "configured": bool(deepseek_key),
            "reachable": deepseek_reachable,
            "level": _level(bool(deepseek_key), deepseek_reachable),
        },
        "search": {
            "provider": "serper" if serper_key else "",
            "configured": bool(serper_key),
            "reachable": serper_reachable,
            "level": _level(bool(serper_key), serper_reachable),
        },
        "redaction_enabled": redaction_enabled(),
        "auth_required": auth_required(),
    }
