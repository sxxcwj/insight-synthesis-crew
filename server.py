import os
import sys
import time
import threading
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 确保 src 目录在 sys.path（先于 craw 导入）
# root_dir 可在测试中改到临时目录；页面文件始终从 WEB_DIR 读取。
PACKAGE_ROOT = Path(__file__).resolve().parent
root_dir = PACKAGE_ROOT
WEB_DIR = PACKAGE_ROOT / "web"
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from craw.access_auth import (
    COOKIE_NAME,
    auth_required,
    auth_startup_warning,
    request_authorized,
    secret_matches,
    session_value,
)
from craw.redact import redact_text, redaction_enabled
from craw.runtime_status import build_runtime_status


def resolve_bind_host() -> str:
    return os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1"


def is_loopback_client(request: Request) -> bool:
    host = request.client.host if request.client and request.client.host else ""
    return host in {"127.0.0.1", "::1", "localhost"}


class AccessGate:
    """设置了访问口令时，页面和全部 /api 都要先通过认证。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not auth_required():
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in {"/login", "/login.html", "/api/login", "/api/auth/status"}:
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin1").lower(): value.decode("latin1")
            for key, value in scope.get("headers", [])
        }
        if request_authorized(headers.get("authorization", ""), headers.get("cookie", "")):
            await self.app(scope, receive, send)
            return

        if path.startswith("/api/"):
            response = JSONResponse({"detail": "需要登录"}, status_code=401)
        else:
            response = RedirectResponse(url="/login", status_code=302)
        await response(scope, receive, send)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    warning = auth_startup_warning()
    if warning:
        print(warning)
    yield


app = FastAPI(title="长伴 · 战略研究智能体", lifespan=lifespan)
app.add_middleware(AccessGate)

# 全局任务状态管理
job_state: Dict[str, Any] = {
    "is_running": False,
    "current_topic": "",
    "mode": "flow",
    "stage": "idle",  # idle, scout, gate, analyst, multimodal, done, error
    "progress": 0,
    "logs": [],
    "error": None,
    "start_time": 0,
    "completed_time": 0
}

state_lock = threading.Lock()


def log_event(message: str, stage: Optional[str] = None, progress: Optional[int] = None):
    with state_lock:
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        job_state["logs"].append(entry)
        if stage:
            job_state["stage"] = stage
        if progress is not None:
            job_state["progress"] = progress


def _maybe_open_local_pptx(pptx_path: Path):
    """只在服务绑定本机地址时尝试唤起本机 PowerPoint。"""
    if resolve_bind_host() not in {"127.0.0.1", "::1", "localhost"}:
        return
    if not pptx_path.exists():
        return
    try:
        subprocess.Popen(["open", "-a", "Microsoft PowerPoint", str(pptx_path.resolve())])
        log_event("已尝试用本机 PowerPoint 打开演示文稿", "multimodal", 95)
    except Exception as exc:
        log_event(f"本机未能打开 PowerPoint: {exc}")


def run_research_task(topic: str, mode: str):
    with state_lock:
        job_state["is_running"] = True
        job_state["current_topic"] = topic
        job_state["mode"] = mode
        job_state["stage"] = "scout"
        job_state["progress"] = 15
        job_state["logs"] = []
        job_state["error"] = None
        job_state["start_time"] = time.time()
        job_state["completed_time"] = 0

    log_event(f"启动研究任务: {topic}", "scout", 20)
    if redaction_enabled():
        log_event("外发脱敏已开启：手机号、身份证号、邮箱、银行卡号和已配置的客户企业名称会替换为占位符。")
    log_event("阶段一：检索员正在检索公开资料并保留来源链接。", "scout", 35)

    try:
        if mode == "flow":
            from craw.flow import AdvancedTwoStageFlow
            flow = AdvancedTwoStageFlow()
            flow.state.topic = topic
            log_event(
                "质量门禁：检查底稿是否至少有 2 个链接且不少于 250 字，不足则重试检索（最多 2 次）。",
                "gate",
                55,
            )
            flow.kickoff()
        else:
            from craw.crew import TwoStageResearchCrew
            crew_obj = TwoStageResearchCrew().crew()
            log_event("阶段二：分析员根据检索底稿整理判断，此阶段不再发起公网搜索。", "analyst", 65)
            crew_obj.kickoff(inputs={"topic": topic})

        log_event("正在整理 Word、16:9 幻灯片、趋势图和 Markdown。", "multimodal", 85)
        _maybe_open_local_pptx(root_dir / "reports" / "research_report.pptx")

        log_event("研究交付物已生成。", "done", 100)
        with state_lock:
            job_state["is_running"] = False
            job_state["completed_time"] = time.time()

    except Exception as err:
        log_event(f"运行异常: {err}", "error", 100)
        with state_lock:
            job_state["is_running"] = False
            job_state["error"] = str(err)


class ResearchRequest(BaseModel):
    topic: str
    mode: str = "flow"


class LoginRequest(BaseModel):
    password: str = ""
    token: str = ""


@app.get("/api/auth/status")
def get_auth_status():
    return {"required": auth_required()}


@app.post("/api/login")
def login(body: LoginRequest):
    if not auth_required():
        return {"ok": True, "required": False}
    candidate = body.password or body.token
    if not secret_matches(candidate):
        raise HTTPException(status_code=401, detail="口令不正确")
    response = JSONResponse({"ok": True, "required": True})
    response.set_cookie(
        COOKIE_NAME,
        session_value(),
        httponly=True,
        samesite="lax",
        path="/",
        max_age=7 * 24 * 3600,
    )
    return response


@app.get("/login")
def login_page():
    return FileResponse(WEB_DIR / "login.html", media_type="text/html")


@app.get("/api/status")
def get_runtime_status():
    return build_runtime_status()


@app.get("/api/env-status")
def get_env_status():
    status = build_runtime_status()
    return {
        "deepseek_ready": status["deepseek"]["configured"] and status["deepseek"]["reachable"] is True,
        "serper_ready": status["search"]["configured"] and status["search"]["reachable"] is True,
        "engine": status["model"],
        "model_label": status["model_label"],
        "default_mode": "flow",
    }


@app.get("/api/job-status")
def get_job_status():
    with state_lock:
        return dict(job_state)


@app.post("/api/research")
def start_research(req: ResearchRequest, background_tasks: BackgroundTasks):
    with state_lock:
        if job_state["is_running"]:
            raise HTTPException(status_code=400, detail="当前有正在运行的研究任务，请等待完成。")

    original = req.topic.strip()
    if not original:
        raise HTTPException(status_code=400, detail="研究课题不能为空。")

    topic = redact_text(original)
    background_tasks.add_task(run_research_task, topic, req.mode)
    return {"status": "started", "topic": topic, "mode": req.mode}


@app.get("/api/deliverables")
def get_deliverables():
    reports_dir = root_dir / "reports"
    files = {
        "docx": reports_dir / "research_report.docx",
        "pptx": reports_dir / "research_report.pptx",
        "md": reports_dir / "research_report.md",
        "chart": reports_dir / "research_report_chart.png"
    }

    res = {}
    for key, path in files.items():
        if path.exists():
            stat = path.stat()
            res[key] = {
                "exists": True,
                "name": path.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            }
        else:
            res[key] = {"exists": False}

    md_content = ""
    if files["md"].exists():
        try:
            md_content = files["md"].read_text(encoding="utf-8")
        except Exception:
            pass

    return {"deliverables": res, "markdown_preview": md_content}


@app.get("/api/deliverables/download/{file_type}")
def download_deliverable(file_type: str):
    reports_dir = root_dir / "reports"
    file_map = {
        "docx": ("research_report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "pptx": ("research_report.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        "md": ("research_report.md", "text/markdown"),
        "chart": ("research_report_chart.png", "image/png")
    }

    if file_type not in file_map:
        raise HTTPException(status_code=404, detail="未知文件格式")

    filename, media_type = file_map[file_type]
    file_path = reports_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件尚未生成")

    return FileResponse(file_path, media_type=media_type, filename=filename)


@app.post("/api/open-pptx")
def open_pptx(request: Request):
    if not is_loopback_client(request):
        raise HTTPException(status_code=403, detail="只有通过本机地址访问时才能调用本地 PowerPoint")

    pptx_path = root_dir / "reports" / "research_report.pptx"
    if not pptx_path.exists():
        raise HTTPException(status_code=404, detail="未找到 PPTX 文件")

    try:
        subprocess.Popen(["open", "-a", "Microsoft PowerPoint", str(pptx_path.resolve())])
        return {"status": "opened", "file": str(pptx_path.name)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"打开 PowerPoint 失败: {exc}")


def _archive_dir() -> Path:
    return (root_dir / "reports" / "archive").resolve()


def _safe_archive_file(filename: str) -> Path:
    if (
        not filename
        or filename != Path(filename).name
        or ".." in filename
        or "/" in filename
        or "\\" in filename
    ):
        raise HTTPException(status_code=400, detail="非法文件名")
    archive_dir = _archive_dir()
    target = (archive_dir / filename).resolve()
    if target.parent != archive_dir:
        raise HTTPException(status_code=400, detail="非法路径")
    return target


def _archive_record(path: Path) -> dict:
    parts = path.stem.split("_", 2)
    date_str = parts[0] if len(parts) >= 1 else ""
    topic = parts[2] if len(parts) >= 3 else path.stem
    if len(date_str) == 8 and date_str.isdigit():
        date_label = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    else:
        date_label = date_str
    return {
        "filename": path.name,
        "topic": topic,
        "date": date_label,
        "size_kb": round(path.stat().st_size / 1024, 1),
    }


def _archive_matches(path: Path, record: dict, needle: str) -> bool:
    haystack = f"{record['topic']}\n{record['filename']}".lower()
    if needle in haystack:
        return True
    try:
        content = path.read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        return False
    return needle in content


@app.get("/api/archives")
def get_archives(q: str = ""):
    archive_dir = root_dir / "reports" / "archive"
    if not archive_dir.exists():
        return {"archives": []}

    needle = q.strip().lower()
    archives = []
    for path in sorted(archive_dir.glob("*.md"), reverse=True):
        record = _archive_record(path)
        if needle and not _archive_matches(path, record, needle):
            continue
        archives.append(record)
    return {"archives": archives}


@app.get("/api/archives/content/{filename}")
def get_archive_content(filename: str):
    target = _safe_archive_file(filename)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="档案文件不存在")
    try:
        content = target.read_text(encoding="utf-8")
        return {"filename": filename, "content": content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/api/archives/{filename}")
def delete_archive(filename: str):
    target = _safe_archive_file(filename)
    archive_dir = _archive_dir()
    if not target.is_file():
        raise HTTPException(status_code=404, detail="档案文件不存在")

    removed: List[str] = []
    for suffix in (".md", ".docx", ".pptx", ".png"):
        sibling = archive_dir / f"{target.stem}{suffix}"
        if not sibling.is_file():
            continue
        resolved = sibling.resolve()
        if resolved.parent != archive_dir:
            continue
        resolved.unlink()
        removed.append(resolved.name)

    if not removed:
        raise HTTPException(status_code=404, detail="档案文件不存在")
    return {"deleted": filename, "removed": removed}


# 挂载静态文件。显式路由（含 /login）优先于该挂载。
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    host = resolve_bind_host()
    port = int(os.getenv("PORT", "8000") or "8000")
    print(f"长伴 · 战略研究智能体: http://{host}:{port}")
    uvicorn.run("server:app", host=host, port=port, reload=True)
