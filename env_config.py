import os
from typing import Dict

def read_env_file() -> Dict[str, str]:
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key, value = parts
                        env_vars[key] = value
    return env_vars

def write_env_file(env_vars: Dict[str, str]) -> None:
    lines = []
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
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

    with open('.env', 'w') as f:
        f.writelines(new_lines)
