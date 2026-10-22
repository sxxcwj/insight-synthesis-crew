import os
import sys
import tempfile
from pathlib import Path

src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from craw.redact import redact_text


ENV_KEYS = ("REDACTION_ENABLED", "REDACTION_CLIENT_NAMES", "REDACTION_CLIENTS_FILE")


def _restore_env(old):
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _clear_redaction_env():
    old = {key: os.environ.get(key) for key in ENV_KEYS}
    for key in ENV_KEYS:
        os.environ.pop(key, None)
    return old


def test_redacts_phone_id_email_and_bank_card():
    old = _clear_redaction_env()
    try:
        text = (
            "联系人张三，手机 13800138000，邮箱 User@Example.com，"
            "身份证 110101199003078515，卡号 4111 1111 1111 1111。"
            "课题本身是制造业薪酬体系对标。"
        )
        redacted = redact_text(text)
        assert "13800138000" not in redacted
        assert "User@Example.com" not in redacted
        assert "110101199003078515" not in redacted
        assert "4111" not in redacted
        assert "[手机号]" in redacted
        assert "[邮箱]" in redacted
        assert "[身份证号]" in redacted
        assert "[银行卡号]" in redacted
        assert "制造业薪酬体系对标" in redacted
    finally:
        _restore_env(old)


def test_redacts_configured_client_names_longest_first():
    text = redact_text(
        "请比较华新制造与华新制造集团的调薪策略",
        client_names=["华新制造", "华新制造集团"],
        enabled=True,
    )
    assert text == "请比较[客户企业1]与[客户企业2]的调薪策略"


def test_client_names_from_env_and_file():
    old = _clear_redaction_env()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            clients = Path(tmp) / "clients.txt"
            clients.write_text("# 注释\n华北示例机电有限公司\n", encoding="utf-8")
            os.environ["REDACTION_ENABLED"] = "true"
            os.environ["REDACTION_CLIENT_NAMES"] = "虚构客户科技股份有限公司"
            os.environ["REDACTION_CLIENTS_FILE"] = str(clients)
            redacted = redact_text("虚构客户科技股份有限公司拜访华北示例机电有限公司")
            assert "虚构客户科技股份有限公司" not in redacted
            assert "华北示例机电有限公司" not in redacted
            assert "[客户企业1]" in redacted
            assert "[客户企业2]" in redacted
    finally:
        _restore_env(old)


def test_redaction_is_on_by_default_and_can_be_disabled():
    old = _clear_redaction_env()
    try:
        assert "[手机号]" in redact_text("手机13812345678")
        os.environ["REDACTION_ENABLED"] = "false"
        assert redact_text("手机13812345678，华新制造") == "手机13812345678，华新制造"
        os.environ["REDACTION_ENABLED"] = "off"
        raw = "a@b.cn"
        assert redact_text(raw, client_names=["华新制造"]) == raw
    finally:
        _restore_env(old)


def test_does_not_redact_ordinary_numbers():
    old = _clear_redaction_env()
    try:
        text = "2026年调薪幅度约 8%，样本 120 家。"
        assert redact_text(text, enabled=True) == text
    finally:
        _restore_env(old)


if __name__ == "__main__":
    test_redacts_phone_id_email_and_bank_card()
    test_redacts_configured_client_names_longest_first()
    test_client_names_from_env_and_file()
    test_redaction_is_on_by_default_and_can_be_disabled()
    test_does_not_redact_ordinary_numbers()
    print("脱敏测试通过")
