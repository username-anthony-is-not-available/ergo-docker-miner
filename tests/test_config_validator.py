import json
from pathlib import Path

import pytest

from config_validator import validate_configuration


@pytest.fixture
def valid_config() -> dict[str, str]:
    return {
        "MINER": "lolminer",
        "POOL_ADDRESS": "stratum+tcp://erg.2miners.com:8080",
        "WALLET_ADDRESS": "sample-wallet-address",
        "GPU_DEVICES": "0,1",
        "MULTI_PROCESS": "true",
        "API_PORT": "4444",
        "HOST_BIND_ADDRESS": "127.0.0.1",
        "APPLY_OC": "false",
        "AUTO_PROFIT_SWITCHING": "false",
        "TELEGRAM_ENABLE": "false",
        "CHECK_NODE_SYNC": "false",
        "AUTO_RESTART_ON_CUDA_ERROR": "false",
    }


@pytest.fixture
def valid_profiles(tmp_path: Path) -> Path:
    profiles_path = tmp_path / "gpu_profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "RTX 3070": {
                    "GPU_CLOCK_OFFSET": -200,
                    "GPU_MEM_OFFSET": 800,
                    "GPU_POWER_LIMIT": 250,
                    "GPU_TEMP_THRESHOLD": 80,
                }
            }
        ),
        encoding="utf-8",
    )
    return profiles_path


def test_accepts_valid_configuration(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    assert validate_configuration(valid_config, valid_profiles) == []


def test_shipped_environment_example_is_valid() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config: dict[str, str] = {}
    env_example = project_root / ".env.example"
    for raw_line in env_example.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            config[name] = value

    assert validate_configuration(config, project_root / "gpu_profiles.json") == []


def test_compose_passes_interpolated_host_binding_to_each_service() -> None:
    project_root = Path(__file__).resolve().parents[1]
    expected = '"HOST_BIND_ADDRESS=${HOST_BIND_ADDRESS:-127.0.0.1}"'
    compose_files = (
        "docker-compose.yml",
        "docker-compose.multi-gpu.yml",
        "docker-compose.multi-gpu.amd.yml",
    )

    for filename in compose_files:
        content = (project_root / filename).read_text(encoding="utf-8")
        services: list[str] = []
        current: list[str] = []
        in_services = False
        for line in content.splitlines():
            if line == "services:":
                in_services = True
                continue
            if not in_services:
                continue
            if line and not line.startswith(" "):
                break
            if line.startswith("  ") and not line.startswith("    "):
                if current:
                    services.append("\n".join(current))
                current = [line]
            elif current:
                current.append(line)
        if current:
            services.append("\n".join(current))

        assert len(services) == 2, filename
        assert all(expected in service for service in services), filename


def test_requires_pool_and_wallet_before_startup(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    valid_config.pop("POOL_ADDRESS")
    valid_config.pop("WALLET_ADDRESS")

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("POOL_ADDRESS is required" in error for error in errors)
    assert any("WALLET_ADDRESS is required" in error for error in errors)


def test_test_mode_does_not_bypass_required_pool_and_wallet(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    valid_config.pop("POOL_ADDRESS")
    valid_config.pop("WALLET_ADDRESS")
    valid_config["TEST_MODE"] = "1"

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("POOL_ADDRESS is required" in error for error in errors)
    assert any("WALLET_ADDRESS is required" in error for error in errors)


def test_rejects_unsupported_miner(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    valid_config["MINER"] = "unknown-miner"

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("MINER must be one of" in error for error in errors)


@pytest.mark.parametrize("value", ["yes", "TRUE", "1", "enabled"])
def test_rejects_unsupported_boolean_spelling(
    valid_config: dict[str, str], valid_profiles: Path, value: str
) -> None:
    valid_config["MULTI_PROCESS"] = value

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("MULTI_PROCESS must be 'true' or 'false'" in error for error in errors)


@pytest.mark.parametrize("value", ["0,,1", "1,1", "-1", "0,", "gpu0"])
def test_rejects_invalid_gpu_device_lists(
    valid_config: dict[str, str], valid_profiles: Path, value: str
) -> None:
    valid_config["GPU_DEVICES"] = value

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("GPU_DEVICES" in error for error in errors)


def test_accepts_auto_gpu_selection(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    valid_config["GPU_DEVICES"] = "AUTO"

    assert validate_configuration(valid_config, valid_profiles) == []


@pytest.mark.parametrize("value", ["0", "65536", "not-a-port"])
def test_rejects_invalid_api_ports(
    valid_config: dict[str, str], valid_profiles: Path, value: str
) -> None:
    valid_config["API_PORT"] = value

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("API_PORT" in error for error in errors)


def test_rejects_multi_process_port_overflow(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    valid_config["API_PORT"] = "65535"

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("API_PORT plus GPU count" in error for error in errors)


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("GPU_CLOCK_OFFSET", "not-a-number", "GPU_CLOCK_OFFSET must be an integer"),
        ("GPU_POWER_LIMIT", "0", "GPU_POWER_LIMIT must be between 1 and 1000"),
        ("GPU_POWER_LIMIT", "250.5", "GPU_POWER_LIMIT must be an integer"),
        ("GPU_TEMP_THRESHOLD", "151", "GPU_TEMP_THRESHOLD must be between 1 and 150"),
    ],
)
def test_rejects_invalid_gpu_environment_values(
    valid_config: dict[str, str],
    valid_profiles: Path,
    name: str,
    value: str,
    message: str,
) -> None:
    valid_config[name] = value

    errors = validate_configuration(valid_config, valid_profiles)

    assert any(message in error for error in errors)


def test_accepts_bracketed_ipv6_host_binding(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    valid_config["HOST_BIND_ADDRESS"] = "[::1]"

    assert validate_configuration(valid_config, valid_profiles) == []


def test_rejects_unbracketed_ipv6_host_binding(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    valid_config["HOST_BIND_ADDRESS"] = "::1"

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("IPv6 HOST_BIND_ADDRESS must be bracketed" in error for error in errors)


def test_rejects_invalid_pool_url(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    valid_config["POOL_ADDRESS"] = "https://example.com"

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("POOL_ADDRESS must be a valid stratum URL" in error for error in errors)


def test_rejects_malformed_gpu_profile_json(
    valid_config: dict[str, str], tmp_path: Path
) -> None:
    profiles_path = tmp_path / "gpu_profiles.json"
    profiles_path.write_text("{not valid json", encoding="utf-8")

    errors = validate_configuration(valid_config, profiles_path)

    assert any("gpu_profiles.json is not valid JSON" in error for error in errors)


def test_rejects_invalid_gpu_temperature_threshold(
    valid_config: dict[str, str], tmp_path: Path
) -> None:
    profiles_path = tmp_path / "gpu_profiles.json"
    profiles_path.write_text(
        json.dumps({"RTX 3070": {"GPU_TEMP_THRESHOLD": 999}}),
        encoding="utf-8",
    )

    errors = validate_configuration(valid_config, profiles_path)

    assert any("GPU_TEMP_THRESHOLD" in error for error in errors)


def test_rejects_fractional_gpu_power_limit_profile(
    valid_config: dict[str, str], tmp_path: Path
) -> None:
    profiles_path = tmp_path / "gpu_profiles.json"
    profiles_path.write_text(
        json.dumps({"RTX 3070": {"GPU_POWER_LIMIT": 250.5}}),
        encoding="utf-8",
    )

    errors = validate_configuration(valid_config, profiles_path)

    assert any("GPU_POWER_LIMIT must be an integer" in error for error in errors)


def test_accepts_documented_profile_without_temperature_threshold(
    valid_config: dict[str, str], tmp_path: Path
) -> None:
    profiles_path = tmp_path / "gpu_profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "RTX 3070": {
                    "GPU_CLOCK_OFFSET": -200,
                    "GPU_MEM_OFFSET": 1300,
                    "GPU_POWER_LIMIT": 130,
                }
            }
        ),
        encoding="utf-8",
    )

    assert validate_configuration(valid_config, profiles_path) == []


def test_rejects_unknown_selected_gpu_profile(
    valid_config: dict[str, str], valid_profiles: Path
) -> None:
    valid_config["GPU_PROFILE"] = "RTX 9990"

    errors = validate_configuration(valid_config, valid_profiles)

    assert any("GPU_PROFILE 'RTX 9990' is not defined" in error for error in errors)
