#!/usr/bin/env python3
#
# inject-mcp-token.py
#
# Replace `${ZAI_MCP_TOKEN}` placeholders in the installed plugin's .mcp.json
# with the value of the ZAI_MCP_TOKEN environment variable.
#
# Background: ZCode does not expand environment variables inside MCP config,
# so the token must be substituted manually after the plugin is installed.
# This is the Python cross-platform counterpart of dev-plugin's
# inject-mcp-token.{sh,ps1} scripts.
#
# Behavior:
#   - Reads token from env var ZAI_MCP_TOKEN (errors out if missing/empty)
#   - Locates the newest installed x.y.z version dir under the plugin cache
#     (or uses the one passed via --version)
#   - Backs up .mcp.json to .mcp.json.bak before editing
#   - Idempotent: a file with no placeholder is treated as success (no rewrite)
#   - Robust to special chars in the token (uses literal str.replace, not regex)
#   - Preserves UTF-8 without BOM and original newline style (LF/CRLF)
#
# Usage:
#   python scripts/inject-mcp-token.py
#   python scripts/inject-mcp-token.py --version 1.2.0
#

import argparse
import os
import re
import sys
from pathlib import Path

# ----------------------------- config -----------------------------
PLUGIN_GROUP = "wakita-plugins"
PLUGIN_NAME = "wakita-toolkit"
PLACEHOLDER = "${ZAI_MCP_TOKEN}"
TARGET_FILE = ".mcp.json"


def err(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)


def locate_install_root() -> Path:
    """Locate the plugin cache root across platforms."""
    home = Path.home()
    return home / ".zcode" / "cli" / "plugins" / "cache" / PLUGIN_GROUP / PLUGIN_NAME


def detect_latest_version(install_root: Path) -> str:
    """Pick the newest x.y.z directory under install_root.

    Uses packaging.version-style tuple sort so 1.10.0 > 1.9.0.
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
        err("Pass the version explicitly:  python scripts/inject-mcp-token.py --version 1.2.0")
        sys.exit(1)
    versions.sort(key=lambda v: v[0])
    return versions[-1][1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inject ZAI_MCP_TOKEN into the installed plugin's .mcp.json",
    )
    parser.add_argument("--version", help="Target a specific installed version (e.g. 1.2.0)")
    args = parser.parse_args()

    # ----------------------------- validate token -----------------------------
    token = os.environ.get("ZAI_MCP_TOKEN", "").strip()
    if not token:
        err("env var ZAI_MCP_TOKEN is not set or empty.")
        print("Run:  export ZAI_MCP_TOKEN='<your zhipu api key>'", file=sys.stderr)
        print("(Windows PowerShell:  $env:ZAI_MCP_TOKEN = '<your key>')", file=sys.stderr)
        print("(persist with setx on Windows, or ~/.zshrc/~/.bashrc on macOS/Linux)", file=sys.stderr)
        return 1

    # ----------------------------- locate plugin dir -----------------------------
    install_root = locate_install_root()
    if not install_root.exists():
        err(f"plugin install dir not found: {install_root}")
        err("Please install the plugin in the ZCode client first, then re-run this script.")
        return 1

    version = args.version or detect_latest_version(install_root)
    version_dir = install_root / version
    mcp_file = version_dir / TARGET_FILE

    if not mcp_file.is_file():
        err(f"target file not found: {mcp_file}")
        err(f"Check that version ({version}) is correct and the plugin is fully installed.")
        return 1

    print(f"Target version: {version}")
    print(f"Target file:    {mcp_file}")

    # ----------------------------- idempotency check -----------------------------
    raw = mcp_file.read_bytes()
    if not raw:
        err(f"file is empty: {mcp_file}")
        return 1

    # Detect newline style from the raw bytes (LF vs CRLF), preserve on write
    if b"\r\n" in raw:
        nl = "\r\n"
    else:
        nl = "\n"

    text = raw.decode("utf-8")
    if PLACEHOLDER not in text:
        print(f"Note: placeholder {PLACEHOLDER} not found; file looks already substituted. Nothing to do.")
        print("Done (no changes).")
        return 0

    # ----------------------------- backup -----------------------------
    backup = mcp_file.with_suffix(mcp_file.suffix + ".bak")
    backup.write_bytes(raw)
    print(f"Backup:         {backup}")

    # ----------------------------- perform replacement -----------------------------
    # Literal str.replace so token chars like / & \ are safe (no regex escaping).
    new_text = text.replace(PLACEHOLDER, token)

    # Write back UTF-8 without BOM, preserving original newline style.
    # Since we read with decode() on bytes and only did str.replace, the
    # newline bytes are preserved as-is when we encode back to utf-8.
    mcp_file.write_bytes(new_text.encode("utf-8"))

    # ----------------------------- verify -----------------------------
    after = mcp_file.read_bytes().decode("utf-8")
    if PLACEHOLDER in after:
        err(f"placeholder still present after substitution; backup kept at {backup} for rollback.")
        return 1

    count = after.count(token)
    print(f"Substitution OK: {count} occurrence(s) written.")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
