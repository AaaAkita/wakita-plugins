#!/usr/bin/env python3
#
# inject-agent-model.py
#
# Set the `model:` field in the frontmatter of the three wakita-governance
# agent files (wakita-scout.md, wakita-builder.md, wakita-auditor.md) under
# the INSTALLED plugin dir.
#
# The model value has the form:  custom:<provider-key>:<model-id>
#   - provider-key: read from ~/.zcode/v2/config.json; colons are URL-encoded
#     to %3A because ':' is the field separator (e.g. builtin:bigmodel ->
#     builtin%3Abigmodel). A UUID key like the default DeepSeek one needs no
#     encoding.
#   - model-id: a model key nested under the chosen provider in config.json.
#
# This is the Python cross-platform counterpart of dev-plugin's
# inject-agent-model.{sh,ps1} scripts. Key improvement: handles BOTH
# dict and list provider structures in config.json (dev-plugin's ps1
# fails on list form, which is why "Windows can't read provider info"
# was reported).
#
# Defaults to DeepSeek deepseek-v4-flash (matches the shipped frontmatter):
#   provider = 466f2f41-bacb-4168-b493-d0afa32a0357
#   modelid  = deepseek-v4-flash
#
# Usage:
#   python scripts/inject-agent-model.py                       # default, latest installed version
#   python scripts/inject-agent-model.py --list                # list all providers and models
#   python scripts/inject-agent-model.py --version 2.0.4
#   python scripts/inject-agent-model.py --provider <key> --model <id>
#
# Behavior:
#   - If an agent file has a `model:` line, replace it in place.
#   - If it has no `model:` line, insert one right before the closing `---`
#     of the frontmatter.
#   - Backs up each file to <file>.bak before editing.
#   - Idempotent: re-running with the same value is a no-op (exit 0).
#   - Validates that provider and model exist in config.json before writing.
#   - Preserves UTF-8 without BOM and original newline style (LF/CRLF).
#

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

# ----------------------------- config -----------------------------
PLUGIN_GROUP = "wakita-plugins"
PLUGIN_NAME = "wakita-governance"
CONFIG_PATH = Path.home() / ".zcode" / "v2" / "config.json"
INSTALL_ROOT = (
    Path.home() / ".zcode" / "cli" / "plugins" / "cache" / PLUGIN_GROUP / PLUGIN_NAME
)
AGENTS_SUBDIR = "agents"
AGENT_FILES = ["wakita-scout.md", "wakita-builder.md", "wakita-auditor.md"]

# defaults: DeepSeek deepseek-v4-flash (matches shipped frontmatter)
DEFAULT_PROVIDER = "466f2f41-bacb-4168-b493-d0afa32a0357"
DEFAULT_MODEL = "deepseek-v4-flash"


def err(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)


# ----------------------------- provider parsing (dict | list) -----------------------------
def load_providers(cfg_path: Path) -> dict:
    """Load config.json and return providers as a unified dict.

    Handles two structures observed across ZCode versions:
      1. dict form (current): cfg["provider"] = { "<key>": {name, models, ...}, ... }
      2. list form (fallback): cfg["provider"] = [ {key/id, name, models, ...}, ... ]

    Returns: { provider_key: { "name": str, "enabled": bool, "models": { model_id: ... } } }

    Raises SystemExit on parse failure.
    """
    if not cfg_path.is_file():
        err(f"config file not found: {cfg_path}")
        err("Cannot verify provider/model. Ensure ZCode is initialized.")
        sys.exit(1)

    try:
        raw = cfg_path.read_bytes().decode("utf-8-sig")  # tolerate BOM
        cfg = json.loads(raw)
    except json.JSONDecodeError as e:
        err(f"failed to parse {cfg_path}: {e}")
        sys.exit(1)

    provider_field = cfg.get("provider")
    if provider_field is None:
        err(f"'provider' field missing in {cfg_path}")
        sys.exit(1)

    def _normalize_models(models):
        """Models could be dict or list; normalize to dict."""
        if isinstance(models, dict):
            return models
        if isinstance(models, list):
            return {
                (m.get("id") or m.get("name") or str(i)): m
                for i, m in enumerate(models)
                if isinstance(m, dict)
            }
        return {}

    unified: dict = {}

    if isinstance(provider_field, dict):
        # Form 1: dict
        for key, val in provider_field.items():
            if not isinstance(val, dict):
                continue
            unified[key] = {
                "name": val.get("name", key),
                "enabled": bool(val.get("enabled", False)),
                "models": _normalize_models(val.get("models", {})),
            }

    elif isinstance(provider_field, list):
        # Form 2: list (fallback for older ZCode versions)
        for item in provider_field:
            if not isinstance(item, dict):
                continue
            # Try common key fields
            key = item.get("key") or item.get("id") or item.get("name")
            if not key:
                continue
            unified[str(key)] = {
                "name": item.get("name", str(key)),
                "enabled": bool(item.get("enabled", False)),
                "models": _normalize_models(item.get("models", {})),
            }

    else:
        err(
            f"unexpected 'provider' type {type(provider_field).__name__} in {cfg_path}; "
            f"expected dict or list"
        )
        sys.exit(1)

    return unified


def list_providers(providers: dict) -> None:
    """Print all providers and their models in a readable table."""
    print(f"{'Provider Key':<48} {'Name':<30} {'Enabled':<8} {'#Models':<8}")
    print("-" * 98)
    for key, info in providers.items():
        name = str(info.get("name", "?"))[:29]
        enabled = "✓" if info.get("enabled") else " "
        n = len(info.get("models", {}))
        print(f"{key:<48} {name:<30} {enabled:<8} {n:<8}")
        # Show model ids indented
        for mid in info.get("models", {}).keys():
            print(f"  model: {mid}")


def print_providers_json(providers: dict) -> None:
    """Print providers as JSON for command/slash-command consumption.

    Output schema:
    {
      "providers": [
        { "key": str, "name": str, "enabled": bool, "models": [str, ...] },
        ...
      ]
    }
    """
    out = {
        "providers": [
            {
                "key": key,
                "name": str(info.get("name", key)),
                "enabled": bool(info.get("enabled", False)),
                "models": list(info.get("models", {}).keys()),
            }
            for key, info in providers.items()
        ]
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ----------------------------- locate plugin dir -----------------------------
def detect_latest_version(install_root: Path) -> str:
    """Pick the newest x.y.z directory under install_root.

    Uses tuple sort so 1.10.0 > 1.9.0 (lexicographic sort would pick 1.9.0).
    """
    pattern = re.compile(r"^\d+\.\d+\.\d+$")
    versions = []
    for entry in install_root.iterdir():
        if entry.is_dir() and pattern.match(entry.name):
            parts = entry.name.split(".")
            try:
                versions.append((tuple(int(p) for p in parts), entry.name))
            except ValueError:
                continue
    if not versions:
        err(f"no version directory (x.y.z) found under {install_root}")
        err(f"Pass the version explicitly:  python scripts/inject-agent-model.py --version 2.0.4")
        sys.exit(1)
    versions.sort(key=lambda v: v[0])
    return versions[-1][1]


# ----------------------------- per-file edit -----------------------------
def edit_agent_file(path: Path, value: str) -> bool:
    """Edit one agent file's frontmatter `model:` field.

    Returns True on success, False on error.
    """
    if not path.is_file():
        print(f"  {path.name:<28} skip: file not found", file=sys.stderr)
        return False

    raw = path.read_bytes()
    if not raw:
        print(f"  {path.name:<28} error: file is empty", file=sys.stderr)
        return False

    # Detect newline style and preserve it
    if b"\r\n" in raw:
        nl = "\r\n"
    else:
        nl = "\n"

    text = raw.decode("utf-8")
    # Strip a single trailing newline for line processing, remember to re-add
    had_trailing_nl = text.endswith(nl)
    body = text[: -len(nl)] if had_trailing_nl else text
    lines = body.split(nl)

    model_line = f'model: "{value}"'

    # 0) idempotency: already the target value (with or without quotes)
    target_with_quotes = f'model: "{value}"'
    target_without_quotes = f"model: {value}"
    for ln in lines:
        trimmed = ln.strip()
        if trimmed == target_with_quotes or trimmed == target_without_quotes:
            print(f"  {path.name:<28} already set, skip")
            return True

    # backup (raw bytes to preserve exact original)
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_bytes(raw)

    # 1) replace existing ^model: line (case-sensitive)
    replaced = False
    for i, ln in enumerate(lines):
        if re.match(r"^model:", ln):
            lines[i] = model_line
            replaced = True
            break

    # 2) no model line -> insert before the closing '---' of the frontmatter
    if not replaced:
        if not lines or lines[0].strip() != "---":
            print(
                f"  {path.name:<28} error: no frontmatter opener '---' on line 1",
                file=sys.stderr,
            )
            return False
        inserted = False
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines.insert(i, model_line)
                inserted = True
                break
        if not inserted:
            print(
                f"  {path.name:<28} error: no closing '---' found in frontmatter",
                file=sys.stderr,
            )
            return False

    # write back with SAME newline style, UTF-8 without BOM
    out = nl.join(lines)
    if had_trailing_nl:
        out += nl
    path.write_bytes(out.encode("utf-8"))
    print(f"  {path.name:<28} updated -> {value}")
    return True


# ----------------------------- main -----------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inject model value into wakita-governance agent frontmatter",
    )
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help=f"Provider key (default: {DEFAULT_PROVIDER})")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--version", help="Target a specific installed version (e.g. 2.0.4)")
    parser.add_argument("--list", action="store_true", help="List all providers and models (human-readable), then exit")
    parser.add_argument("--json", action="store_true", help="List all providers and models as JSON, then exit (for slash command)")
    parser.add_argument("--apply", action="store_true", help="Actually write the change; without this flag, --provider/--model only validate and print what would happen")
    args = parser.parse_args()

    providers = load_providers(CONFIG_PATH)

    # ---- read-only modes: --list / --json ----
    if args.json:
        # Structured output for slash command consumption.
        print_providers_json(providers)
        return 0

    if args.list:
        list_providers(providers)
        return 0

    # ----------------------------- sanity: provider/model non-empty -----------------------------
    if not args.provider or not args.model:
        err("--provider and --model must both be non-empty.")
        return 2

    # ----------------------------- validate against config.json -----------------------------
    if args.provider not in providers:
        err(f"provider '{args.provider}' not found in {CONFIG_PATH}")
        err("Available providers:")
        for k, info in providers.items():
            print(f"   - {k}  ({info.get('name', '?')})", file=sys.stderr)
        return 1

    prov_info = providers[args.provider]
    if args.model not in prov_info.get("models", {}):
        err(f"model '{args.model}' not found under provider '{args.provider}'.")
        err("Available models for this provider:")
        for mid in prov_info.get("models", {}).keys():
            print(f"   - {mid}", file=sys.stderr)
        return 1

    # ----------------------------- build model value -----------------------------
    # URL-encode ':' in provider key to %3A (it's the field separator in the value).
    provider_enc = args.provider.replace(":", "%3A")
    model_value = f"custom:{provider_enc}:{args.model}"

    # ----------------------------- dry-run guard: require --apply to write ----
    if not args.apply:
        # Dry-run: print the planned change as JSON for the slash command to parse,
        # but do NOT touch any file.
        print(json.dumps({
            "dry_run": True,
            "provider": args.provider,
            "provider_name": prov_info.get("name", args.provider),
            "model": args.model,
            "model_value": model_value,
            "note": "Re-run with --apply to actually write the change.",
        }, ensure_ascii=False, indent=2))
        return 0

    # ----------------------------- locate plugin dir -----------------------------
    if not INSTALL_ROOT.exists():
        err(f"plugin install dir not found: {INSTALL_ROOT}")
        err("Please install the plugin in the ZCode client first, then re-run this script.")
        return 1

    version = args.version or detect_latest_version(INSTALL_ROOT)
    version_dir = INSTALL_ROOT / version
    agents_dir = version_dir / AGENTS_SUBDIR

    if not agents_dir.is_dir():
        err(f"agents dir not found: {agents_dir}")
        return 1

    # ----------------------------- per-file edit -----------------------------
    updated_files = []
    skipped_files = []
    failed_files = []
    for af in AGENT_FILES:
        result = edit_agent_file_quiet(agents_dir / af, model_value)
        if result == "updated":
            updated_files.append(af)
        elif result == "skip":
            skipped_files.append(af)
        else:
            failed_files.append(af)

    if failed_files:
        err(f"Completed with errors on: {failed_files}")
        return 1

    # ----------------------------- structured success output (for slash command) ----
    print(json.dumps({
        "ok": True,
        "applied": True,
        "version": version,
        "provider": args.provider,
        "provider_name": prov_info.get("name", args.provider),
        "model": args.model,
        "model_value": model_value,
        "updated_files": updated_files,
        "skipped_files": skipped_files,
        "restart_hint": (
            "ZCode 当前不支持热重载已加载的 agent。需新开会话让新 model 生效。"
            "请关闭当前会话或重启 ZCode 客户端。"
        ),
    }, ensure_ascii=False, indent=2))
    return 0


def edit_agent_file_quiet(path: Path, value: str) -> str:
    """Same as edit_agent_file but returns a status string instead of printing.

    Returns: "updated" | "skip" | "failed"
    """
    if not path.is_file():
        return "failed"

    raw = path.read_bytes()
    if not raw:
        return "failed"

    if b"\r\n" in raw:
        nl = "\r\n"
    else:
        nl = "\n"

    text = raw.decode("utf-8")
    had_trailing_nl = text.endswith(nl)
    body = text[: -len(nl)] if had_trailing_nl else text
    lines = body.split(nl)

    model_line = f'model: "{value}"'

    # idempotency
    target_with_quotes = f'model: "{value}"'
    target_without_quotes = f"model: {value}"
    for ln in lines:
        trimmed = ln.strip()
        if trimmed == target_with_quotes or trimmed == target_without_quotes:
            return "skip"

    # backup
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_bytes(raw)

    # replace or insert
    replaced = False
    for i, ln in enumerate(lines):
        if re.match(r"^model:", ln):
            lines[i] = model_line
            replaced = True
            break

    if not replaced:
        if not lines or lines[0].strip() != "---":
            return "failed"
        inserted = False
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines.insert(i, model_line)
                inserted = True
                break
        if not inserted:
            return "failed"

    out = nl.join(lines)
    if had_trailing_nl:
        out += nl
    path.write_bytes(out.encode("utf-8"))
    return "updated"


if __name__ == "__main__":
    sys.exit(main())
