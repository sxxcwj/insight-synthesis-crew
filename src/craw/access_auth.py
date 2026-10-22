"""可选的页面和接口访问认证。口令只从环境变量读取，不写入代码。"""

import base64
import hashlib
import hmac
import os


COOKIE_NAME = "changban_session"
_SESSION_LABEL = b"changban-web-session-v1"


def configured_secrets() -> list[str]:
    secrets: list[str] = []
    for key in ("APP_PASSWORD", "ACCESS_TOKEN"):
        value = os.getenv(key, "").strip()
        if value:
            secrets.append(value)
    return secrets


def auth_required() -> bool:
    return bool(configured_secrets())


def auth_startup_warning() -> str | None:
    if auth_required():
        return None
    return (
        "警告: 未设置 APP_PASSWORD 或 ACCESS_TOKEN，访问认证未启用。"
        "本机模式可直接打开页面；若以后部署到服务器，请先设置其中一项。"
    )


def _equals(left: str, right: str) -> bool:
    left_bytes = left.encode()
    right_bytes = right.encode()
    if not left_bytes or not right_bytes or len(left_bytes) != len(right_bytes):
        return False
    return hmac.compare_digest(left_bytes, right_bytes)


def secret_matches(candidate: str) -> bool:
    candidate = (candidate or "").strip()
    return any(_equals(candidate, secret) for secret in configured_secrets())


def session_value() -> str:
    material = "|".join(configured_secrets()).encode()
    return hmac.new(material, _SESSION_LABEL, hashlib.sha256).hexdigest()


def _cookie_value(cookie_header: str, name: str) -> str:
    for part in cookie_header.split(";"):
        key, separator, value = part.strip().partition("=")
        if separator and key == name:
            return value
    return ""


def _basic_password(authorization: str) -> str:
    if not authorization.lower().startswith("basic "):
        return ""
    encoded = authorization.split(" ", 1)[1].strip()
    try:
        decoded = base64.b64decode(encoded).decode("utf-8", errors="ignore")
    except Exception:
        return ""
    _, separator, password = decoded.partition(":")
    return password if separator else ""


def request_authorized(authorization: str = "", cookie_header: str = "") -> bool:
    if not auth_required():
        return True
    session = _cookie_value(cookie_header, COOKIE_NAME)
    if session and _equals(session, session_value()):
        return True
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if secret_matches(token):
            return True
    basic_password = _basic_password(authorization)
    if basic_password and secret_matches(basic_password):
        return True
    return False
