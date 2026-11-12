import os
from collections.abc import Mapping
from pathlib import Path

SENSITIVE_SECRET_VARS: tuple[str, ...] = (
    "WALLET_ADDRESS",
    "DUAL_WALLET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "DISCORD_WEBHOOK_URL",
)


def get_env_file_path() -> str:
    """Return the path to the active .env configuration file."""
    return os.path.join(os.getenv('DATA_DIR', '.'), '.env')


def _read_secret_file(path: Path) -> str | None:
    """Read a secret file and strip trailing CR/LF characters if it exists."""
    try:
        if path.is_file():
            value = path.read_text(encoding='utf-8').rstrip('\r\n')
            return value if value else None
    except OSError:
        return None
    return None


def get_secret(
    var_name: str,
    default: str | None = None,
    secrets_dir: str | Path = '/run/secrets',
    env: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve a sensitive configuration value from env, ``<VAR>_FILE``, or Docker secrets.

    Resolution order:
    1. Explicit non-empty environment variable ``var_name``.
    2. File path specified by ``<var_name>_FILE``.
    3. Default Docker secret path ``<secrets_dir>/<var_name>``.
    4. ``default``.
    """
    source = os.environ if env is None else env
    direct_value = source.get(var_name, '').strip()
    if direct_value:
        return direct_value

    file_override = source.get(f'{var_name}_FILE', '').strip()
    if file_override:
        loaded = _read_secret_file(Path(file_override))
        if loaded is not None:
            return loaded

    default_secret = _read_secret_file(Path(secrets_dir) / var_name)
    if default_secret is not None:
        return default_secret

    return default


def resolve_secrets_into_env(
    env: Mapping[str, str],
    secrets_dir: str | Path = '/run/secrets',
) -> dict[str, str]:
    """Return a copy of ``env`` populated with any Docker secrets for sensitive variables."""
    resolved = dict(env)
    for var_name in SENSITIVE_SECRET_VARS:
        if not resolved.get(var_name, '').strip():
            secret_value = get_secret(var_name, secrets_dir=secrets_dir, env=resolved)
            if secret_value is not None:
                resolved[var_name] = secret_value
    return resolved


def read_env_file() -> dict[str, str]:
    """Read key-value pairs from the configured .env file."""
    env_vars = {}
    env_file = get_env_file_path()
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key, value = parts
                        env_vars[key] = value
    return env_vars


def write_env_file(env_vars: dict[str, str]) -> None:
    """Persist updated key-value pairs to the configured .env file."""
    lines = []
    env_file = get_env_file_path()
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            lines = f.readlines()

    new_lines = []
    keys_written = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0]
            if key in env_vars:
                new_lines.append(f"{key}={env_vars[key]}\n")
                keys_written.add(key)
                continue
        new_lines.append(line)

    for key, value in env_vars.items():
        if key not in keys_written:
            new_lines.append(f"{key}={value}\n")

    with open(env_file, 'w') as f:
        f.writelines(new_lines)
