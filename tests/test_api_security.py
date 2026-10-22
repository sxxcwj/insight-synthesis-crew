import os
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "src"))

import server
from fastapi.testclient import TestClient

import craw.runtime_status as runtime_status


ENV_KEYS = (
    "APP_PASSWORD",
    "ACCESS_TOKEN",
    "DEEPSEEK_API_KEY",
    "SERPER_API_KEY",
    "SCOUT_LLM_MODEL",
    "ANALYST_LLM_MODEL",
    "REDACTION_ENABLED",
    "REDACTION_CLIENT_NAMES",
    "REDACTION_CLIENTS_FILE",
    "HOST",
    "PORT",
)


class isolated_env:
    def __init__(self, **values):
        self.values = values
        self.previous = {}

    def __enter__(self):
        self.previous = {key: os.environ.get(key) for key in ENV_KEYS}
        for key in ENV_KEYS:
            os.environ.pop(key, None)
        for key, value in self.values.items():
            if value is not None:
                os.environ[key] = value
        return self

    def __exit__(self, exc_type, exc, tb):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return False


def _use_reports(tmp: Path):
    reports = tmp / "reports"
    archive = reports / "archive"
    archive.mkdir(parents=True)
    (reports / "research_report.md").write_text("# 预览\n\nhttps://example.com/hr\n", encoding="utf-8")
    (reports / "research_report.docx").write_bytes(b"docx")
    (reports / "research_report.pptx").write_bytes(b"pptx")
    (archive / "20261022_120000_薪酬对标.md").write_text(
        "# 薪酬对标\n\n正文独有词甲乙丙\n", encoding="utf-8"
    )
    (archive / "20261022_120000_薪酬对标.docx").write_bytes(b"docx")
    (archive / "20261022_120000_薪酬对标.pptx").write_bytes(b"pptx")
    (archive / "20261022_120000_薪酬对标.png").write_bytes(b"png")
    (archive / "20261022_130000_继任计划.md").write_text("# 继任计划\n", encoding="utf-8")
    return reports


def test_bind_host_defaults_to_loopback_and_auth_warns_when_open():
    with isolated_env():
        assert server.resolve_bind_host() == "127.0.0.1"
        warning = server.auth_startup_warning()
        assert warning
        assert "APP_PASSWORD" in warning
        assert "ACCESS_TOKEN" in warning
    with isolated_env(HOST="0.0.0.0", APP_PASSWORD="local-only"):
        assert server.resolve_bind_host() == "0.0.0.0"
        assert server.auth_startup_warning() is None


def test_auth_protects_pages_and_every_api():
    with tempfile.TemporaryDirectory() as tmp:
        previous_root = server.root_dir
        server.root_dir = Path(tmp)
        _use_reports(server.root_dir)
        try:
            with isolated_env(APP_PASSWORD="secret-pass"):
                client = TestClient(server.app)
                assert client.get("/api/auth/status").json()["required"] is True
                for path in (
                    "/api/job-status",
                    "/api/status",
                    "/api/archives",
                    "/api/deliverables",
                    "/api/deliverables/download/md",
                    "/api/archives/content/20261022_130000_继任计划.md",
                ):
                    assert client.get(path).status_code == 401, path
                assert client.post("/api/open-pptx").status_code == 401
                page = client.get("/", follow_redirects=False)
                assert page.status_code == 302
                assert page.headers["location"].endswith("/login")
                assert client.get("/login").status_code == 200
                assert "长伴" in client.get("/login").text
                denied = client.post("/api/login", json={"password": "wrong"})
                assert denied.status_code == 401
                allowed = client.post("/api/login", json={"password": "secret-pass"})
                assert allowed.status_code == 200
                assert "changban_session" in allowed.headers.get("set-cookie", "")
                assert client.get("/api/archives").status_code == 200
                downloaded = client.get("/api/deliverables/download/md")
                assert downloaded.status_code == 200
                assert client.get("/api/archives/content/20261022_130000_继任计划.md").status_code == 200
        finally:
            server.root_dir = previous_root


def test_access_token_and_basic_auth_are_accepted():
    with tempfile.TemporaryDirectory() as tmp:
        previous_root = server.root_dir
        server.root_dir = Path(tmp)
        _use_reports(server.root_dir)
        try:
            with isolated_env(ACCESS_TOKEN="tok-123", APP_PASSWORD="pw"):
                bearer = TestClient(server.app)
                assert bearer.get("/api/status").status_code == 401
                bearer.headers["Authorization"] = "Bearer tok-123"
                assert bearer.get("/api/deliverables/download/docx").status_code == 200
                basic = TestClient(server.app)
                assert basic.get("/api/archives", auth=("changban", "pw")).status_code == 200
                assert basic.get("/api/archives", auth=("changban", "nope")).status_code == 401
        finally:
            server.root_dir = previous_root


def test_status_reports_real_model_and_reachability():
    original_deepseek = runtime_status.probe_deepseek_reachable
    original_serper = runtime_status.probe_serper_reachable
    try:
        with isolated_env(SCOUT_LLM_MODEL="deepseek/deepseek-chat", ANALYST_LLM_MODEL="deepseek/deepseek-chat"):
            def explode(*args, **kwargs):
                raise AssertionError("未配置时不应探测外网")

            runtime_status.probe_deepseek_reachable = explode
            runtime_status.probe_serper_reachable = explode
            client = TestClient(server.app)
            missing = client.get("/api/status").json()
            assert missing["model"] == "deepseek/deepseek-chat"
            assert missing["deepseek"]["configured"] is False
            assert missing["deepseek"]["reachable"] is None
            assert missing["deepseek"]["level"] == "red"
            assert missing["search"]["level"] == "red"
            assert "DeepSeek-V3" not in str(missing)

        with isolated_env(
            DEEPSEEK_API_KEY="dk",
            SERPER_API_KEY="sk",
            SCOUT_LLM_MODEL="deepseek/deepseek-flash",
            ANALYST_LLM_MODEL="deepseek/deepseek-reasoner",
        ):
            runtime_status.probe_deepseek_reachable = lambda api_key, timeout=2.5: False
            runtime_status.probe_serper_reachable = lambda api_key, timeout=2.5: True
            client = TestClient(server.app)
            data = client.get("/api/status").json()
            assert data["model"] == "deepseek/deepseek-flash"
            assert data["analyst_model"] == "deepseek/deepseek-reasoner"
            assert data["deepseek"]["level"] == "yellow"
            assert data["deepseek"]["configured"] is True
            assert data["deepseek"]["reachable"] is False
            assert data["search"]["configured"] is True
            assert data["search"]["reachable"] is True
            assert data["search"]["level"] == "green"
            assert "DeepSeek-V3" not in str(data)
            legacy = client.get("/api/env-status").json()
            assert legacy["engine"] == "deepseek/deepseek-flash"
            assert "DeepSeek-V3" not in str(legacy)
    finally:
        runtime_status.probe_deepseek_reachable = original_deepseek
        runtime_status.probe_serper_reachable = original_serper


def test_research_redacts_topic_before_external_dispatch():
    captured = {}
    original = server.run_research_task

    def fake_run(topic, mode):
        captured["topic"] = topic
        captured["mode"] = mode

    server.run_research_task = fake_run
    server.job_state["is_running"] = False
    try:
        with isolated_env(REDACTION_ENABLED="true", REDACTION_CLIENT_NAMES="虚构客户制造有限公司"):
            client = TestClient(server.app)
            response = client.post(
                "/api/research",
                json={
                    "topic": "虚构客户制造有限公司 联系 13800138000 与 hr@client.example",
                    "mode": "crew",
                },
            )
            assert response.status_code == 200
            assert captured["mode"] == "crew"
            assert "13800138000" not in captured["topic"]
            assert "hr@client.example" not in captured["topic"]
            assert "虚构客户制造有限公司" not in captured["topic"]
            assert "[手机号]" in captured["topic"]
            assert "[邮箱]" in captured["topic"]
            assert "[客户企业1]" in captured["topic"]
    finally:
        server.run_research_task = original
        server.job_state["is_running"] = False


def test_archive_search_delete_and_path_guard():
    with tempfile.TemporaryDirectory() as tmp:
        previous_root = server.root_dir
        server.root_dir = Path(tmp)
        reports = _use_reports(server.root_dir)
        archive = reports / "archive"
        try:
            with isolated_env():
                client = TestClient(server.app)
                by_body = client.get("/api/archives", params={"q": "独有词甲乙丙"}).json()["archives"]
                assert [item["filename"] for item in by_body] == ["20261022_120000_薪酬对标.md"]
                by_topic = client.get("/api/archives", params={"q": "继任"}).json()["archives"]
                assert len(by_topic) == 1
                assert by_topic[0]["topic"] == "继任计划"
                everything = client.get("/api/archives").json()["archives"]
                assert len(everything) == 2

                removed = client.delete("/api/archives/20261022_120000_薪酬对标.md")
                assert removed.status_code == 200
                assert not (archive / "20261022_120000_薪酬对标.md").exists()
                assert not (archive / "20261022_120000_薪酬对标.docx").exists()
                assert not (archive / "20261022_120000_薪酬对标.pptx").exists()
                assert not (archive / "20261022_120000_薪酬对标.png").exists()
                assert (archive / "20261022_130000_继任计划.md").exists()

                escaped = client.get("/api/archives/content/..%2F..%2Fpyproject.toml")
                assert escaped.status_code in (400, 404, 405)
                assert "[project]" not in escaped.text
                rejected = client.delete("/api/archives/..%2F..%2Fpyproject.toml")
                assert rejected.status_code in (400, 404, 405)
                assert client.delete("/api/archives/..secret.md").status_code == 400
                assert (root / "pyproject.toml").exists()
        finally:
            server.root_dir = previous_root


def test_open_pptx_only_for_loopback_client():
    with tempfile.TemporaryDirectory() as tmp:
        previous_root = server.root_dir
        previous_popen = server.subprocess.Popen
        server.root_dir = Path(tmp)
        _use_reports(server.root_dir)
        called = {}

        def fake_popen(cmd, *args, **kwargs):
            called["cmd"] = cmd
            return None

        server.subprocess.Popen = fake_popen
        try:
            with isolated_env():
                remote = TestClient(server.app)
                assert remote.post("/api/open-pptx").status_code == 403
                assert "cmd" not in called
                local = TestClient(server.app, client=("127.0.0.1", 50000))
                opened = local.post("/api/open-pptx")
                assert opened.status_code == 200
                assert called["cmd"][0] == "open"
        finally:
            server.subprocess.Popen = previous_popen
            server.root_dir = previous_root


if __name__ == "__main__":
    test_bind_host_defaults_to_loopback_and_auth_warns_when_open()
    test_auth_protects_pages_and_every_api()
    test_access_token_and_basic_auth_are_accepted()
    test_status_reports_real_model_and_reachability()
    test_research_redacts_topic_before_external_dispatch()
    test_archive_search_delete_and_path_guard()
    test_open_pptx_only_for_loopback_client()
    print("接口安全测试通过")
