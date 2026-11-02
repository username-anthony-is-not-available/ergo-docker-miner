"""Regression checks for secure, host-scoped Docker Compose port publishing."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOST_BIND_ADDRESS = "${HOST_BIND_ADDRESS:-127.0.0.1}"
HOST_BIND_PREFIX = HOST_BIND_ADDRESS + ":"
PORT_KEYS = {"target", "published", "host_ip", "protocol", "mode"}
COMPOSE_PATTERNS = (
    "docker-compose*.yml",
    "docker-compose*.yaml",
    "compose*.yml",
    "compose*.yaml",
)
IGNORED_DIRECTORIES = {".git", ".venv", "venv", "node_modules"}


def discover_compose_files() -> list[Path]:
    """Find Compose manifests throughout the checkout, not a fixed file list."""
    files = {path for pattern in COMPOSE_PATTERNS for path in ROOT.rglob(pattern)}
    return sorted(
        path
        for path in files
        if not IGNORED_DIRECTORIES.intersection(path.relative_to(ROOT).parts[:-1])
    )


def _strip_comment(value: str) -> str:
    """Remove a YAML comment while preserving quoted `#` characters."""
    quote = None
    for index, character in enumerate(value):
        if quote:
            if character == quote and (index == 0 or value[index - 1] != "\\"):
                quote = None
        elif character in {'"', "'"}:
            quote = character
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.strip()


def _unquote(value: str) -> str:
    value = _strip_comment(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _inline_mapping(value: str) -> dict[str, str]:
    pairs = re.findall(
        r"([A-Za-z_][\w-]*)\s*:\s*(\"[^\"]*\"|'[^']*'|[^,}]+)",
        value,
    )
    return {key: _unquote(item) for key, item in pairs}


def _split_flow_items(value: str) -> list[str]:
    """Split a simple YAML flow sequence at commas outside quotes and maps."""
    items = []
    start = 0
    depth = 0
    quote = None
    for index, character in enumerate(value):
        if quote:
            if character == quote and (index == 0 or value[index - 1] != "\\"):
                quote = None
        elif character in {'"', "'"}:
            quote = character
        elif character in "[{":
            depth += 1
        elif character in "]}":
            depth -= 1
        elif character == "," and depth == 0:
            items.append(value[start:index].strip())
            start = index + 1
    tail = value[start:].strip()
    if tail:
        items.append(tail)
    return items


def _parse_port_item(value: str) -> tuple[str, str | dict[str, str]]:
    value = _strip_comment(value).strip()
    if value.startswith("{") and value.endswith("}"):
        return "long", _inline_mapping(value[1:-1])
    key_value = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", value)
    if key_value and key_value.group(1) in PORT_KEYS:
        return "long", {key_value.group(1): _unquote(key_value.group(2))}
    return "short", _unquote(value)


def extract_port_entries(text: str) -> list[tuple[str, str | dict[str, str]]]:
    """Extract scalar and long-form entries from YAML `ports` sections."""
    lines = text.splitlines()
    entries: list[tuple[str, str | dict[str, str]]] = []
    index = 0

    while index < len(lines):
        header = re.match(r"^( *)ports\s*:\s*(.*?)\s*$", lines[index])
        if not header:
            index += 1
            continue

        section_indent = len(header.group(1))
        inline_value = _strip_comment(header.group(2)).strip()
        if inline_value.startswith("[") and inline_value.endswith("]"):
            for item in _split_flow_items(inline_value[1:-1]):
                entries.append(_parse_port_item(item))
        elif inline_value and inline_value not in {"null", "~"}:
            entries.append(_parse_port_item(inline_value))

        index += 1
        current_long: dict[str, str] | None = None
        item_indent = -1
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                index += 1
                continue

            indent = len(line) - len(line.lstrip(" "))
            if indent <= section_indent:
                break

            if stripped.startswith("-"):
                if current_long is not None:
                    entries.append(("long", current_long))
                current_long = None
                item_indent = indent
                item_value = stripped[1:].strip()
                if not item_value:
                    current_long = {}
                else:
                    kind, parsed = _parse_port_item(item_value)
                    if kind == "long" and item_value.startswith("{"):
                        entries.append((kind, parsed))
                    elif kind == "long":
                        assert isinstance(parsed, dict)
                        current_long = parsed
                    else:
                        entries.append((kind, parsed))
            elif current_long is not None and indent > item_indent:
                key_value = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", stripped)
                if key_value and key_value.group(1) in PORT_KEYS:
                    current_long[key_value.group(1)] = _unquote(key_value.group(2))
            index += 1

        if current_long is not None:
            entries.append(("long", current_long))

    return entries


def assert_safe_binding(entry: tuple[str, str | dict[str, str]]) -> None:
    """Require the Compose-time host override to default to loopback."""
    kind, value = entry
    if kind == "short":
        assert isinstance(value, str)
        if not value.startswith(HOST_BIND_PREFIX):
            raise AssertionError(
                f"port mapping lacks loopback-default host IP: {value}"
            )
        ports = value[len(HOST_BIND_PREFIX) :].split(":")
        valid_port = re.compile(r"\d+(?:-\d+)?(?:/(?:tcp|udp|sctp))?$")
        if len(ports) != 2 or not all(valid_port.fullmatch(port) for port in ports):
            raise AssertionError(f"invalid short-form port mapping: {value}")
        return

    assert isinstance(value, dict)
    if value.get("host_ip") != HOST_BIND_ADDRESS:
        raise AssertionError(f"long-form port lacks loopback-default host_ip: {value}")
    for key in ("target", "published"):
        port = value.get(key)
        if port is not None and not re.fullmatch(r"\d+(?:-\d+)?", port):
            raise AssertionError(f"invalid long-form {key} port: {value}")
    if "target" not in value:
        raise AssertionError(f"long-form port is missing its target: {value}")


class ComposePortBindingTests(unittest.TestCase):
    def test_every_discovered_published_port_defaults_to_loopback(self) -> None:
        compose_files = discover_compose_files()
        self.assertTrue(compose_files, "No Compose manifests found")
        total = 0
        for compose_file in compose_files:
            text = compose_file.read_text(encoding="utf-8")
            entries = extract_port_entries(text)
            has_ports_block = re.search(r"^ *ports\s*:", text, re.MULTILINE)
            if has_ports_block:
                self.assertTrue(
                    entries, f"Could not parse ports in {compose_file.name}"
                )
            total += len(entries)
            for entry in entries:
                with self.subTest(compose_file=compose_file.name, entry=entry):
                    assert_safe_binding(entry)
        self.assertGreater(total, 0, "No published Compose ports were checked")

    def test_unquoted_wildcard_mapping_is_detected_and_rejected(self) -> None:
        fixture = "services:\n  miner:\n    ports:\n      - 0.0.0.0:5999:5999\n"
        entries = extract_port_entries(fixture)
        self.assertEqual(entries, [("short", "0.0.0.0:5999:5999")])
        with self.assertRaisesRegex(AssertionError, "loopback-default"):
            assert_safe_binding(entries[0])

    def test_flow_list_wildcard_mapping_is_detected_and_rejected(self) -> None:
        fixture = "services:\n  miner:\n    ports: [0.0.0.0:5999:5999]\n"
        entries = extract_port_entries(fixture)
        self.assertEqual(entries, [("short", "0.0.0.0:5999:5999")])
        with self.assertRaisesRegex(AssertionError, "loopback-default"):
            assert_safe_binding(entries[0])

    def test_long_form_wildcard_mapping_is_rejected(self) -> None:
        fixture = (
            "services:\n  miner:\n    ports:\n"
            "      - target: 5999\n        published: '5999'\n"
            "        host_ip: 0.0.0.0\n"
        )
        entries = extract_port_entries(fixture)
        self.assertEqual(len(entries), 1)
        with self.assertRaisesRegex(AssertionError, "loopback-default"):
            assert_safe_binding(entries[0])

    def test_long_form_loopback_mapping_is_accepted(self) -> None:
        fixture = (
            "services:\n  miner:\n    ports:\n"
            f'      - target: 5999\n        published: "5999"\n'
            f'        host_ip: "{HOST_BIND_ADDRESS}"\n'
        )
        entries = extract_port_entries(fixture)
        self.assertEqual(len(entries), 1)
        assert_safe_binding(entries[0])

    def test_bracketed_ipv6_override_uses_valid_short_syntax(self) -> None:
        compose_text = "\n".join(
            path.read_text(encoding="utf-8") for path in discover_compose_files()
        )
        mappings = [
            value
            for kind, value in extract_port_entries(compose_text)
            if kind == "short" and isinstance(value, str)
        ]
        self.assertTrue(mappings, "No short-form Compose port mappings found")
        for mapping in mappings:
            rendered = mapping.replace(HOST_BIND_ADDRESS, "[::1]", 1)
            self.assertRegex(rendered, r"^\[::1\]:\d+(?:-\d+)?:\d+(?:-\d+)?$")

    def test_example_environment_uses_loopback_default(self) -> None:
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("HOST_BIND_ADDRESS=127.0.0.1", example)


if __name__ == "__main__":
    unittest.main()
