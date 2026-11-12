import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _extract_copied_files(dockerfile_text: str) -> set[str]:
    """Return the set of top-level filenames copied in the Dockerfile COPY instructions."""
    copied: set[str] = set()
    lines = dockerfile_text.splitlines()
    joined_lines: list[str] = []
    buffer = ""
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith("\\"):
            buffer += stripped[:-1] + " "
        else:
            joined_lines.append(buffer + stripped)
            buffer = ""

    for line in joined_lines:
        if line.startswith("COPY ") and "--from=" not in line:
            parts = line.split()[1:]
            if len(parts) >= 2:
                copied.update(parts[:-1])
    return copied


def test_dockerfile_uses_multi_stage_and_non_root_user() -> None:
    content = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "AS miner-builder" in content
    assert "AS python-builder" in content
    assert "useradd -u 1000 -g miner" in content
    assert "gosu miner" in (PROJECT_ROOT / "start.sh").read_text(encoding="utf-8")


def test_dockerfile_copies_all_runtime_python_modules_and_scripts() -> None:
    content = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    copied = _extract_copied_files(content)

    expected_runtime_files = {
        "start.sh",
        "healthcheck.sh",
        "restart.sh",
        "gpu_profiles.json",
        "logrotate.conf",
        "config_validator.py",
        "database.py",
        "discord_notifier.py",
        "env_config.py",
        "log_monitor.py",
        "metrics.py",
        "miner_api.py",
        "network_retry.py",
        "price_fetcher.py",
        "profit_switcher.py",
        "report_generator.py",
        "streamlit_app.py",
    }
    missing = expected_runtime_files - copied
    assert not missing, f"Missing runtime files in Dockerfile COPY: {missing}"

    # Verify all local Python imports used by copied Python modules are also copied
    local_modules = {p.stem for p in PROJECT_ROOT.glob("*.py")}
    for filename in sorted(f for f in expected_runtime_files if f.endswith(".py")):
        tree = ast.parse((PROJECT_ROOT / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in local_modules:
                        assert f"{alias.name}.py" in copied
            elif isinstance(node, ast.ImportFrom) and node.module in local_modules:
                assert f"{node.module}.py" in copied


def test_dockerfile_orders_application_copy_after_dependency_installs() -> None:
    content = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    venv_copy_idx = content.index("COPY --from=python-builder /opt/venv")
    miner_copy_idx = content.index("COPY --from=miner-builder /app/lolMiner")
    app_copy_idx = content.index("COPY start.sh")

    assert venv_copy_idx < app_copy_idx
    assert miner_copy_idx < app_copy_idx
    assert "find /opt/venv -type d -name '__pycache__'" in content


def test_dockerignore_excludes_non_runtime_directories_and_keeps_runtime_files() -> None:
    ignore_lines = {
        line.strip()
        for line in (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    for pattern in (".git", "node_modules", "tests", "*.md", ".env", "__pycache__"):
        assert pattern in ignore_lines

    dockerfile_copied = _extract_copied_files(
        (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    )
    for runtime_file in dockerfile_copied:
        assert runtime_file not in ignore_lines
