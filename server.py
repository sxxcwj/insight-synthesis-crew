import os
import sys
import time
import threading
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# 确保 src 目录在 sys.path
root_dir = Path(__file__).resolve().parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

app = FastAPI(title="Insight Synthesis Studio 4A Gateway")

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

    log_event(f"🚀 启动研究任务: {topic}", "scout", 20)
    log_event("🔎 [阶段一: Scout] 正在执行全网广度情报检索与去噪...", "scout", 35)

    try:
        if mode == "flow":
            from craw.flow import AdvancedTwoStageFlow
            flow = AdvancedTwoStageFlow()
            flow.state.topic = topic
            log_event("🛡️ [质量门禁] 激活自愈质量门禁与反幻觉核验机制...", "gate", 55)
            flow.kickoff()
        else:
            from craw.crew import TwoStageResearchCrew
            crew_obj = TwoStageResearchCrew().crew()
            log_event("⚡ [阶段二: Analyst] 深度战略推演与洞察提炼...", "analyst", 65)
            crew_obj.kickoff(inputs={"topic": topic})

        log_event("🎨 [多模态生成] 渲染 300 DPI 趋势图表并编译 Word & 16:9 PPTX...", "multimodal", 85)
        
        # 检查生成成果并触发 Mac PPT 打开规则
        pptx_path = root_dir / "reports" / "research_report.pptx"
        if pptx_path.exists():
            try:
                subprocess.Popen(["open", "-a", "Microsoft PowerPoint", str(pptx_path.resolve())])
                log_event("🖥️ 已自动调用系统 Microsoft PowerPoint 打开 16:9 演示文稿", "multimodal", 95)
            except Exception as e:
                log_event(f"提示: 尝试打开 PowerPoint 演示文稿: {e}")

        log_event("✅ [全部完成] 全格式成果交付包已就绪！", "done", 100)
        with state_lock:
            job_state["is_running"] = False
            job_state["completed_time"] = time.time()

    except Exception as err:
        log_event(f"❌ 运行异常: {err}", "error", 100)
        with state_lock:
            job_state["is_running"] = False
            job_state["error"] = str(err)


class ResearchRequest(BaseModel):
    topic: str
    mode: str = "flow"


@app.get("/api/env-status")
def get_env_status():
    deepseek_key = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    serper_key = bool(os.getenv("SERPER_API_KEY", "").strip())
    return {
        "deepseek_ready": deepseek_key,
        "serper_ready": serper_key,
        "engine": "DeepSeek-V3 / Flash",
        "default_mode": "flow"
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

    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="研究课题不能为空。")

    background_tasks.add_task(run_research_task, req.topic.strip(), req.mode)
    return {"status": "started", "topic": req.topic, "mode": req.mode}


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

    # 读取 markdown 摘要前 2000 字用于快速预览
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
def open_pptx():
    pptx_path = root_dir / "reports" / "research_report.pptx"
    if not pptx_path.exists():
        raise HTTPException(status_code=404, detail="未找到 PPTX 文件")

    try:
        subprocess.Popen(["open", "-a", "Microsoft PowerPoint", str(pptx_path.resolve())])
        return {"status": "opened", "file": str(pptx_path.name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开 PowerPoint 失败: {e}")


@app.get("/api/archives")
def get_archives():
    archive_dir = root_dir / "reports" / "archive"
    if not archive_dir.exists():
        return {"archives": []}

    md_files = sorted(list(archive_dir.glob("*.md")), reverse=True)
    archives = []
    for f in md_files:
        clean_name = f.stem
        parts = clean_name.split("_", 2)
        date_str = parts[0] if len(parts) >= 1 else ""
        time_str = parts[1] if len(parts) >= 2 else ""
        topic = parts[2] if len(parts) >= 3 else clean_name
        archives.append({
            "filename": f.name,
            "topic": topic,
            "date": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str,
            "size_kb": round(f.stat().st_size / 1024, 1)
        })

    return {"archives": archives}


@app.get("/api/archives/content/{filename}")
def get_archive_content(filename: str):
    archive_dir = root_dir / "reports" / "archive"
    target = archive_dir / filename
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="档案文件不存在")

    try:
        content = target.read_text(encoding="utf-8")
        return {"filename": filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 挂载静态文件
app.mount("/", StaticFiles(directory=str(root_dir / "web"), html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
