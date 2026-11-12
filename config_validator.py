"""Validate miner environment configuration before startup side effects."""

from __future__ import annotations

import ipaddress
import json
import math
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

from env_config import get_secret, resolve_secrets_into_env

BOOLEAN_VARIABLES = (
    "APPLY_OC",
    "AUTO_PROFIT_SWITCHING",
    "AUTO_RESTART_ON_CUDA_ERROR",
    "CHECK_NODE_SYNC",
    "MULTI_PROCESS",
    "TELEGRAM_ENABLE",
)
PROFILE_NUMERIC_KEYS = (
    "GPU_CLOCK_OFFSET",
    "GPU_MEM_OFFSET",
    "GPU_POWER_LIMIT",
    "GPU_TEMP_THRESHOLD",
)
PROFILE_INTEGER_KEYS = {
    "GPU_CLOCK_OFFSET",
    "GPU_MEM_OFFSET",
    "GPU_POWER_LIMIT",
}
STRATUM_SCHEMES = {"stratum+tcp", "stratum+ssl", "stratum+tls"}


def _is_finite_number(value: float) -> bool:
    """Return whether a JSON/config number is finite, including very large ints."""
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _validate_pool_address(name: str, value: str) -> list[str]:
    """Return validation errors for a stratum pool URL."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return [f"{name} must be a valid stratum URL with a valid port."]

    if (
        parsed.scheme.lower() not in STRATUM_SCHEMES
        or not parsed.hostname
        or port is None
        or not 1 <= port <= 65535
    ):
        return [
            (
                f"{name} must be a valid stratum URL with scheme stratum+tcp, "
                "stratum+ssl, or stratum+tls and a port from 1 to 65535."
            )
        ]
    return []


def _validate_gpu_profiles(path: Path) -> tuple[dict[str, object], list[str]]:
    """Load the GPU profile JSON and validate each known numeric setting."""
    if not path.exists():
        return {}, []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, ["gpu_profiles.json is not valid JSON or cannot be read."]

    if not isinstance(data, dict) or not data:
        return {}, ["gpu_profiles.json must contain a non-empty object of profiles."]

    errors: list[str] = []
    for profile_name, settings in data.items():
        if not isinstance(profile_name, str) or not profile_name.strip():
            errors.append(
                "gpu_profiles.json contains an empty or invalid profile name."
            )
            continue
        if not isinstance(settings, dict):
            errors.append(f"GPU profile '{profile_name}' must contain an object.")
            continue
        if not any(key in settings for key in PROFILE_NUMERIC_KEYS):
            errors.append(f"GPU profile '{profile_name}' has no supported settings.")
            continue
        for key in PROFILE_NUMERIC_KEYS:
            if key not in settings:
                continue
            value = settings[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"GPU profile '{profile_name}' {key} must be numeric.")
                continue
            if key in PROFILE_INTEGER_KEYS and not isinstance(value, int):
                errors.append(f"GPU profile '{profile_name}' {key} must be an integer.")
                continue
            if not _is_finite_number(value):
                errors.append(f"GPU profile '{profile_name}' has non-finite {key}.")
            elif key == "GPU_TEMP_THRESHOLD" and not 1 <= value <= 150:
                errors.append(
                    f"GPU profile '{profile_name}' GPU_TEMP_THRESHOLD must be 1..150."
                )
            elif key == "GPU_POWER_LIMIT" and not 1 <= value <= 1000:
                errors.append(
                    f"GPU profile '{profile_name}' GPU_POWER_LIMIT must be 1..1000."
                )
    return data, errors


def validate_configuration(
    config: Mapping[str, str], profiles_path: Path | str
) -> list[str]:
    """Validate miner environment values and the optional GPU profiles file.

    Args:
        config: Environment values supplied by Docker Compose or the shell.
        profiles_path: Path to the GPU profile JSON file.

    Returns:
        A list of actionable errors. An empty list means the configuration is valid.
    """
    errors: list[str] = []
    profile_path = Path(profiles_path)

    miner = config.get("MINER", "lolminer").strip() or "lolminer"
    if miner not in {"lolminer", "t-rex"}:
        errors.append("MINER must be one of: lolminer, t-rex.")

    for name in ("POOL_ADDRESS", "BACKUP_POOL_ADDRESS"):
        value = config.get(name, "").strip()
        if name == "POOL_ADDRESS" and not value:
            errors.append("POOL_ADDRESS is required before mining can start.")
        elif value:
            errors.extend(_validate_pool_address(name, value))

    wallet = (get_secret("WALLET_ADDRESS", env=config) or "").strip()
    if not wallet:
        errors.append("WALLET_ADDRESS is required before mining can start.")

    boolean_values: dict[str, str] = {}
    for name in BOOLEAN_VARIABLES:
        value = config.get(name, "false").strip() or "false"
        boolean_values[name] = value
        if value not in {"true", "false"}:
            errors.append(f"{name} must be 'true' or 'false'.")

    raw_devices = config.get("GPU_DEVICES", "AUTO").strip() or "AUTO"
    device_ids: list[int] | None = None
    if raw_devices == "AUTO":
        device_ids = None
    else:
        device_parts = raw_devices.split(",")
        if any(not part.isdigit() for part in device_parts):
            errors.append(
                "GPU_DEVICES must be AUTO or comma-separated non-negative integers."
            )
        else:
            device_ids = [int(part) for part in device_parts]
            if len(device_ids) != len(set(device_ids)):
                errors.append("GPU_DEVICES must not contain duplicate GPU IDs.")

    api_port: int | None = None
    try:
        api_port = int(config.get("API_PORT", "4444").strip() or "4444")
        if not 1 <= api_port <= 65535:
            errors.append("API_PORT must be an integer from 1 to 65535.")
            api_port = None
    except ValueError:
        errors.append("API_PORT must be an integer from 1 to 65535.")

    if (
        api_port is not None
        and boolean_values.get("MULTI_PROCESS") == "true"
        and device_ids
        and api_port + len(device_ids) - 1 > 65535
    ):
        errors.append(
            "API_PORT plus GPU count must not exceed 65535 in multi-process mode."
        )

    for name in PROFILE_NUMERIC_KEYS:
        raw_value = config.get(name, "").strip()
        if not raw_value:
            continue
        try:
            numeric_value = (
                int(raw_value)
                if name in PROFILE_INTEGER_KEYS
                else float(raw_value)
            )
        except ValueError:
            expected = "an integer" if name in PROFILE_INTEGER_KEYS else "numeric"
            errors.append(f"{name} must be {expected}.")
            continue
        if not _is_finite_number(numeric_value):
            errors.append(f"{name} must be a finite number.")
        elif name == "GPU_TEMP_THRESHOLD" and not 1 <= numeric_value <= 150:
            errors.append("GPU_TEMP_THRESHOLD must be between 1 and 150.")
        elif name == "GPU_POWER_LIMIT" and not 1 <= numeric_value <= 1000:
            errors.append("GPU_POWER_LIMIT must be between 1 and 1000.")

    raw_host = config.get("HOST_BIND_ADDRESS", "127.0.0.1").strip() or "127.0.0.1"
    is_bracketed = raw_host.startswith("[") and raw_host.endswith("]")
    host_value = raw_host[1:-1] if is_bracketed else raw_host
    try:
        host_address = ipaddress.ip_address(host_value)
        if host_address.version == 6 and not is_bracketed:
            errors.append(
                "IPv6 HOST_BIND_ADDRESS must be bracketed, for example [::1]."
            )
        if host_address.version == 4 and is_bracketed:
            errors.append("IPv4 HOST_BIND_ADDRESS must not be bracketed.")
    except ValueError:
        errors.append(
            "HOST_BIND_ADDRESS must be a valid IPv4 or bracketed IPv6 address."
        )

    profiles, profile_errors = _validate_gpu_profiles(profile_path)
    errors.extend(profile_errors)
    selected_profile = config.get("GPU_PROFILE", "").strip()
    if selected_profile and selected_profile != "AUTO":
        if profile_path.exists() and profiles and selected_profile not in profiles:
            errors.append(
                f"GPU_PROFILE '{selected_profile}' is not defined in gpu_profiles.json."
            )
        elif not profile_path.exists():
            errors.append("GPU_PROFILE is set but gpu_profiles.json is missing.")

    if config.get("DUAL_ALGO", "").strip():
        if miner != "lolminer":
            errors.append("DUAL_ALGO is supported only when MINER is lolminer.")
        if not config.get("DUAL_POOL", "").strip():
            errors.append("DUAL_POOL is required when DUAL_ALGO is configured.")
        if not (get_secret("DUAL_WALLET", env=config) or "").strip():
            errors.append("DUAL_WALLET is required when DUAL_ALGO is configured.")
        if config.get("DUAL_POOL", "").strip():
            errors.extend(
                _validate_pool_address("DUAL_POOL", config["DUAL_POOL"].strip())
            )

    return errors


def main() -> int:
    """Validate process environment and report any errors without exposing values."""
    profiles_path = Path(__file__).with_name("gpu_profiles.json")
    resolved_env = resolve_secrets_into_env(os.environ)
    errors = validate_configuration(resolved_env, profiles_path)
    if errors:
        print("Invalid miner configuration:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Configuration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
