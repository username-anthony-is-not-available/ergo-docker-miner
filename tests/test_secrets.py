from pathlib import Path

import pytest
import requests

import discord_notifier
import metrics
from config_validator import validate_configuration
from env_config import get_secret, resolve_secrets_into_env


def test_get_secret_prefers_direct_env(tmp_path: Path) -> None:
    secret_file = tmp_path / "WALLET_ADDRESS"
    secret_file.write_text("file-wallet\n", encoding="utf-8")

    value = get_secret(
        "WALLET_ADDRESS",
        secrets_dir=tmp_path,
        env={"WALLET_ADDRESS": "direct-wallet", "WALLET_ADDRESS_FILE": str(secret_file)},
    )

    assert value == "direct-wallet"


def test_get_secret_reads_var_file_override(tmp_path: Path) -> None:
    custom_file = tmp_path / "custom_secret.txt"
    custom_file.write_text("custom-secret-value\r\n", encoding="utf-8")

    value = get_secret(
        "TELEGRAM_BOT_TOKEN",
        secrets_dir=tmp_path,
        env={"TELEGRAM_BOT_TOKEN_FILE": str(custom_file)},
    )

    assert value == "custom-secret-value"


def test_get_secret_reads_default_secrets_dir(tmp_path: Path) -> None:
    secret_file = tmp_path / "DISCORD_WEBHOOK_URL"
    secret_file.write_text("https://discord.com/api/webhooks/123/abc\n", encoding="utf-8")

    value = get_secret("DISCORD_WEBHOOK_URL", secrets_dir=tmp_path, env={})

    assert value == "https://discord.com/api/webhooks/123/abc"


def test_get_secret_returns_default_when_missing_or_empty(tmp_path: Path) -> None:
    (tmp_path / "WALLET_ADDRESS").write_text("\n", encoding="utf-8")

    assert get_secret("WALLET_ADDRESS", default="fallback", secrets_dir=tmp_path, env={}) == "fallback"


def test_resolve_secrets_into_env_populates_sensitive_vars(tmp_path: Path) -> None:
    (tmp_path / "WALLET_ADDRESS").write_text("wallet-from-secret\n", encoding="utf-8")
    (tmp_path / "TELEGRAM_CHAT_ID").write_text("998877\n", encoding="utf-8")

    resolved = resolve_secrets_into_env({"MINER": "lolminer"}, secrets_dir=tmp_path)

    assert resolved["WALLET_ADDRESS"] == "wallet-from-secret"
    assert resolved["TELEGRAM_CHAT_ID"] == "998877"
    assert resolved["MINER"] == "lolminer"


def test_config_validator_accepts_wallet_from_file_secret(tmp_path: Path) -> None:
    wallet_file = tmp_path / "wallet.txt"
    wallet_file.write_text("9gj5C7V6S6v7v6v7v6v7v6v7v6v7v6v7v6v7v6v7v6v7v6v7v6v\n", encoding="utf-8")

    errors = validate_configuration(
        {
            "MINER": "lolminer",
            "POOL_ADDRESS": "stratum+tcp://erg.2miners.com:8080",
            "WALLET_ADDRESS_FILE": str(wallet_file),
        },
        tmp_path / "missing_profiles.json",
    )

    assert errors == []


def test_discord_notifier_uses_secret_and_redacts_webhook_on_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker
) -> None:
    webhook = "https://discord.com/api/webhooks/999/secret-token"
    secret_file = tmp_path / "discord.txt"
    secret_file.write_text(f"{webhook}\n", encoding="utf-8")

    monkeypatch.setattr(discord_notifier, "DISCORD_ENABLE", True)
    monkeypatch.setattr(discord_notifier, "DISCORD_WEBHOOK_URL", None)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL_FILE", str(secret_file))

    mock_post = mocker.patch(
        "discord_notifier.requests.post",
        side_effect=requests.exceptions.RequestException(f"POST failed for {webhook}"),
    )
    mock_log_error = mocker.patch.object(discord_notifier.logger, "error")

    discord_notifier.send_discord_notification("GPU alert")

    mock_post.assert_called_once()
    assert mock_post.call_args.args[0] == webhook
    logged = mock_log_error.call_args.args[0]
    assert "secret-token" not in logged
    assert "<redacted-webhook-url>" in logged


def test_telegram_notifier_uses_secret_and_redacts_token_on_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker
) -> None:
    token = "123456:ABC-SECRET-TOKEN"
    token_file = tmp_path / "tg_token.txt"
    token_file.write_text(f"{token}\n", encoding="utf-8")

    monkeypatch.setattr(metrics, "TELEGRAM_ENABLE", True)
    monkeypatch.setattr(metrics, "TELEGRAM_BOT_TOKEN", None)
    monkeypatch.setattr(metrics, "TELEGRAM_CHAT_ID", "555123")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN_FILE", str(token_file))

    mock_post = mocker.patch(
        "metrics.requests.post",
        side_effect=RuntimeError(f"Error calling https://api.telegram.org/bot{token}/sendMessage"),
    )
    mock_log_error = mocker.patch.object(metrics.logger, "error")

    metrics.send_telegram_notification("Rig alert")

    mock_post.assert_called_once()
    assert token in mock_post.call_args.args[0]
    logged = mock_log_error.call_args.args[0]
    assert token not in logged
    assert "<redacted-bot-token>" in logged
