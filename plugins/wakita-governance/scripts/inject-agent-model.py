#!/usr/bin/env python3
#
# inject-agent-model.py
#
# Generate / update the three wakita-governance subagent files
# (wakita-scout.md, wakita-builder.md, wakita-auditor.md) in the USER-LEVEL
# ZCode subagent directory ~/.zcode/agents/, from the templates shipped in
# this plugin under templates/agents/.
#
# Since v2.4.0 the plugin no longer ships agents under agents/ (which ZCode
# auto-registers as plugin agents). Instead, this script materializes them as
# user-scope subagents so the user can freely edit them, and injects the
# chosen `model:` and `thoughtLevel:` values into the frontmatter.
#
# The model value has the form:  custom:<provider-key>:<model-id>
#   - provider-key: read from ~/.zcode/v2/config.json; colons are URL-encoded
#     to %3A because ':' is the field separator (e.g. builtin:bigmodel ->
#     builtin%3Abigmodel). A UUID key like the default DeepSeek one needs no
#     encoding.
#   - model-id: a model key nested under the chosen provider in config.json.
#
# Defaults to DeepSeek deepseek-v4-flash (matches the shipped scout/builder
# templates; the auditor template ships with deepseek-v4-pro, so a bare
# --apply switches it to flash too — all three agents get ONE unified model):
#   provider = 466f2f41-bacb-4168-b493-d0afa32a0357
#   modelid  = deepseek-v4-flash
#
# Usage:
#   python scripts/inject-agent-model.py                       # default: DeepSeek flash, thoughtLevel from template
#   python scripts/inject-agent-model.py --list                # list all usable providers and models
#   python scripts/inject-agent-model.py --provider <key> --model <id>            # dry-run (no writes)
#   python scripts/inject-agent-model.py --provider <key> --model <id> --apply    # actually write
#   python scripts/inject-agent-model.py --thought-level high --apply             # override thoughtLevel
#
# Behavior:
#   - Renders each templates/agents/wakita-*.md with the new `model:` value
#     (and `thoughtLevel:` when --thought-level is given), then writes the
#     result to ~/.zcode/agents/<name>.md.
#   - Backs up an existing target file to <file>.bak before overwriting.
#   - Idempotent: target file already byte-identical -> skip (exit 0).
#   - Validates that provider and model exist in config.json before writing.
#   - Handles BOTH dict and list provider structures in config.json.
#   - Writes UTF-8 without BOM and preserves the template's newline style.
#

import argparse
import json
import re
import sys
from pathlib import Path

# ----------------------------- config -----------------------------
CONFIG_PATH = Path.home() / ".zcode" / "v2" / "config.json"
USER_AGENTS_DIR = Path.home() / ".zcode" / "agents"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "agents"
AGENT_FILES = ["wakita-scout.md", "wakita-builder.md", "wakita-auditor.md"]

# defaults: DeepSeek deepseek-v4-flash (matches shipped templates)
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

    Returns: { provider_key: { "name": str, "enabled": bool, "usable": bool, "models": {...} } }

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

    def _has_api_key(options: dict) -> bool:
        """Check if a provider's options contain a non-empty API key."""
        api_key = options.get("apiKey", "")
        return bool(api_key) and api_key != "None"

    unified: dict = {}

    if isinstance(provider_field, dict):
        # Form 1: dict
        for key, val in provider_field.items():
            if not isinstance(val, dict):
                continue
            opts = val.get("options", {})
            enabled = bool(val.get("enabled", False))
            has_key = _has_api_key(opts)
            unified[key] = {
                "name": val.get("name", key),
                "enabled": enabled,
                "usable": enabled and has_key,
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
            opts = item.get("options", {})
            enabled = bool(item.get("enabled", False))
            has_key = _has_api_key(opts)
            unified[str(key)] = {
                "name": item.get("name", str(key)),
                "enabled": enabled,
                "usable": enabled and has_key,
                "models": _normalize_models(item.get("models", {})),
            }

    else:
        err(
            f"unexpected 'provider' type {type(provider_field).__name__} in {cfg_path}; "
            f"expected dict or list"
        )
        sys.exit(1)

    return unified


def list_providers(providers: dict, include_disabled: bool = False) -> None:
    """Print providers and their models in a readable table.

    By default only usable providers are shown (enabled + non-empty API key).
    Providers that are enabled but lack an API key are excluded since they
    can't actually be used. Pass include_disabled=True to show all.
    """
    shown = providers if include_disabled else {
        k: v for k, v in providers.items() if v.get("usable")
    }
    if not shown:
        print("(no usable providers; run with --all to see all providers)")
        return
    print(f"{'Provider Key':<48} {'Name':<30} {'Usable':<7} {'Enabled':<8} {'#Models':<8}")
    print("-" * 105)
    for key, info in shown.items():
        name = str(info.get("name", "?"))[:29]
        usable = "✓" if info.get("usable") else " "
        enabled = "✓" if info.get("enabled") else " "
        n = len(info.get("models", {}))
        print(f"{key:<48} {name:<30} {usable:<7} {enabled:<8} {n:<8}")
        # Show model ids indented
        for mid in info.get("models", {}).keys():
            print(f"  model: {mid}")


def resolve_default_provider(providers: dict) -> str:
    """Pick a sensible default provider key when the built-in default is absent.

    Keeps the historical default only when it is *usable* (enabled + non-empty
    API key); otherwise prefers the first usable provider, then any provider,
    and finally returns the historical default unchanged.
    """
    if DEFAULT_PROVIDER in providers and providers[DEFAULT_PROVIDER].get("usable"):
        return DEFAULT_PROVIDER
    usable = [k for k, v in providers.items() if v.get("usable")]
    if usable:
        return usable[0]
    if providers:
        return next(iter(providers))
    return DEFAULT_PROVIDER


def print_providers_json(providers: dict, include_disabled: bool = False) -> None:
    """Print providers as JSON for command/slash-command consumption.

    By default only usable providers are returned (enabled + non-empty API key),
    so the /subagent-create picker only offers providers the user can actually use.
    Pass include_disabled=True to return all.
    """
    shown = providers if include_disabled else {
        k: v for k, v in providers.items() if v.get("usable")
    }
    out = {
        "providers": [
            {
                "key": key,
                "name": str(info.get("name", key)),
                "enabled": bool(info.get("enabled", False)),
                "usable": bool(info.get("usable", False)),
                "models": list(info.get("models", {}).keys()),
            }
            for key, info in shown.items()
        ]
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ----------------------------- template rendering -----------------------------
def render_agent(template_path: Path, model_value: str, thought_level: str | None) -> bytes:
    """Render one agent template with the given model value / thoughtLevel.

    Line-based replacement inside the frontmatter; the body is preserved
    byte-for-byte (only lines starting with `model:` / `thoughtLevel:` change).
    Preserves the template's newline style (LF/CRLF).
    """
    raw = template_path.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    lines = text.split(nl)

    model_replaced = False
    thought_replaced = thought_level is None  # no override -> nothing to do
    in_frontmatter = False
    out_lines = []
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        # Track the frontmatter block (between the opening and closing ---)
        # so replacement can never touch body lines that happen to start
        # with `model:` / `thoughtLevel:`.
        if i == 0 and stripped == "---":
            in_frontmatter = True
            out_lines.append(ln)
            continue
        if in_frontmatter and stripped == "---":
            in_frontmatter = False
            out_lines.append(ln)
            continue
        if in_frontmatter and re.match(r"^model:", ln):
            out_lines.append(f'model: "{model_value}"')
            model_replaced = True
        elif in_frontmatter and thought_level is not None and re.match(r"^thoughtLevel:", ln):
            out_lines.append(f"thoughtLevel: {thought_level}")
            thought_replaced = True
        else:
            out_lines.append(ln)

    if not model_replaced:
        raise ValueError(f"template {template_path.name} has no 'model:' line in frontmatter")
    if not thought_replaced:
        raise ValueError(f"template {template_path.name} has no 'thoughtLevel:' line in frontmatter")

    return nl.join(out_lines).encode("utf-8")


def write_user_agent(target_path: Path, content: bytes) -> str:
    """Write one rendered agent file to the user agents dir.

    Returns: "created" | "updated" | "skip" (already identical).
    Backs up an existing differing file to <file>.bak before overwriting.
    """
    if target_path.is_file():
        existing = target_path.read_bytes()
        if existing == content:
            return "skip"
        target_path.with_suffix(target_path.suffix + ".bak").write_bytes(existing)
        target_path.write_bytes(content)
        return "updated"
    target_path.write_bytes(content)
    return "created"


def target_state(target_path: Path, content: bytes) -> str:
    """Read-only state of a target file vs the content we would write."""
    try:
        if not target_path.is_file():
            return "missing"
        return "identical" if target_path.read_bytes() == content else "will_update"
    except OSError:
        return "unreadable"


# ----------------------------- main -----------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate/update wakita-governance user-level subagents (~/.zcode/agents/) "
        "from plugin templates, injecting model and thoughtLevel into frontmatter",
    )
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help=f"Provider key (default: {DEFAULT_PROVIDER})")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--thought-level", default=None,
                        help="thoughtLevel value to inject (e.g. max/high/low); default: keep template value")
    parser.add_argument("--list", action="store_true", help="List all usable providers and models (enabled + non-empty API key), human-readable, then exit")
    parser.add_argument("--json", action="store_true", help="List all usable providers and models as JSON, then exit (for slash command)")
    parser.add_argument("--all", action="store_true", help="Include disabled/no-key providers in --list/--json output")
    parser.add_argument("--apply", action="store_true", help="Actually write the files; without this flag only a dry-run plan is printed")
    args = parser.parse_args()

    providers = load_providers(CONFIG_PATH)

    # v2.5.0: the historical DeepSeek default key may be absent or disabled /
    # missing an API key on this machine's config.json. Fall back to the first
    # usable provider so bare `--apply` runs keep generating working agents.
    default_usable = (
        DEFAULT_PROVIDER in providers
        and bool(providers[DEFAULT_PROVIDER].get("usable"))
    )
    if args.provider == DEFAULT_PROVIDER and not default_usable:
        fallback = resolve_default_provider(providers)
        if fallback != DEFAULT_PROVIDER:
            print(
                f"Note: default provider '{DEFAULT_PROVIDER}' is not usable in config "
                f"(disabled or missing API key); falling back to '{fallback}'.",
                file=sys.stderr,
            )
        args.provider = fallback

    # ---- read-only modes: --list / --json ----
    if args.json:
        print_providers_json(providers, include_disabled=args.all)
        return 0

    if args.list:
        list_providers(providers, include_disabled=args.all)
        return 0

    # ----------------------------- sanity: provider/model non-empty -----------------------------
    if not args.provider or not args.model:
        err("--provider and --model must both be non-empty.")
        return 2

    thought_level = args.thought_level.strip() if args.thought_level else None
    if args.thought_level is not None and not thought_level:
        err("--thought-level must be non-empty when provided.")
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

    # ----------------------------- locate templates -----------------------------
    if not TEMPLATES_DIR.is_dir():
        err(f"templates dir not found: {TEMPLATES_DIR}")
        err("The plugin installation looks broken (missing templates/agents/). Reinstall wakita-governance.")
        return 1

    # ----------------------------- render all three agents -----------------------------
    rendered: dict[str, bytes] = {}
    for af in AGENT_FILES:
        tpl = TEMPLATES_DIR / af
        if not tpl.is_file():
            err(f"template not found: {tpl}")
            return 1
        try:
            rendered[af] = render_agent(tpl, model_value, thought_level)
        except ValueError as e:
            err(str(e))
            return 1

    effective_thought = thought_level or "(template default)"

    # ----------------------------- dry-run guard: require --apply to write ----
    if not args.apply:
        print(json.dumps({
            "dry_run": True,
            "provider": args.provider,
            "provider_name": prov_info.get("name", args.provider),
            "model": args.model,
            "model_value": model_value,
            "thought_level": effective_thought,
            "target_dir": str(USER_AGENTS_DIR),
            "files": [
                {"file": af, "state": target_state(USER_AGENTS_DIR / af, content)}
                for af, content in rendered.items()
            ],
            "note": "Re-run with --apply to actually write the files.",
        }, ensure_ascii=False, indent=2))
        return 0

    # ----------------------------- write to user agents dir -----------------------------
    try:
        USER_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        err(f"cannot create user agents dir {USER_AGENTS_DIR}: {e}")
        return 1

    created_files = []
    updated_files = []
    skipped_files = []
    failed_files = []
    for af, content in rendered.items():
        try:
            status = write_user_agent(USER_AGENTS_DIR / af, content)
        except OSError as e:
            err(f"failed to write {af}: {e}")
            status = "failed"
        if status == "created":
            created_files.append(af)
        elif status == "updated":
            updated_files.append(af)
        elif status == "skip":
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
        "provider": args.provider,
        "provider_name": prov_info.get("name", args.provider),
        "model": args.model,
        "model_value": model_value,
        "thought_level": effective_thought,
        "target_dir": str(USER_AGENTS_DIR),
        "created_files": created_files,
        "updated_files": updated_files,
        "skipped_files": skipped_files,
        "restart_hint": (
            "ZCode 当前不支持热重载已加载的 agent。需新开会话让子智能体生效。"
            "请关闭当前会话或重启 ZCode 客户端。"
        ),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
