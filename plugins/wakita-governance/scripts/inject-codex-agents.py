#!/usr/bin/env python3
#
# inject-codex-agents.py
#
# Install the three wakita-governance roles (scout / builder / auditor) as
# Codex-native custom agents, plus the three Codex custom-prompt equivalents
# of the ZCode slash commands (/subagent-create, /audit, /lock).
#
# Why this script exists:
#   ZCode defines user-level subagents as Markdown files under ~/.zcode/agents/
#   with frontmatter (model/thoughtLevel/injectAgentsMd). Codex does not read
#   that format. Codex's native mechanism is standalone TOML files under
#   ~/.codex/agents/ (personal) or .codex/agents/ (project-scoped), with the
#   required fields name / description / developer_instructions and optional
#   model / model_reasoning_effort / sandbox_mode / mcp_servers / ...
#   (official docs: developers.openai.com/codex/subagents).
#
#   Codex custom slash commands are Markdown files under ~/.codex/prompts/
#   with YAML frontmatter (description / argument-hint)
#   (official docs: learn.chatgpt.com/docs/custom-prompts).
#
# Usage:
#   python scripts/inject-codex-agents.py --json          # show effective defaults (no writes)
#   python scripts/inject-codex-agents.py --list          # human-readable plan (no writes)
#   python scripts/inject-codex-agents.py                 # dry-run (no writes)
#   python scripts/inject-codex-agents.py --apply         # write agents + prompts
#   python scripts/inject-codex-agents.py --model deepseek-v4-pro --apply
#   python scripts/inject-codex-agents.py --reasoning max --sandbox read-only --apply
#   python scripts/inject-codex-agents.py --no-prompts --apply
#
# Behavior:
#   - Renders templates/codex-agents/wakita-*.toml -> ~/.codex/agents/wakita-*.toml
#     and templates/codex-prompts/wakita-*.md -> ~/.codex/prompts/wakita-*.md.
#   - Backs up an existing differing target to <file>.bak before overwriting.
#   - Idempotent: byte-identical target -> skip.
#   - Validates --model against ~/.codex/models.json when present.
#   - Reads ~/.codex/config.toml only for display defaults; never modifies it.
#   - Writes UTF-8 without BOM and preserves the template's newline style.
#

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.10 fallback
    try:
        import tomli as tomllib
    except ImportError:  # pragma: no cover - no TOML parser available
        tomllib = None


def codex_home() -> Path:
    """Return the Codex home directory (respects $CODEX_HOME, defaults to ~/.codex)."""
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env)
    return Path.home() / ".codex"


CODEX_HOME = codex_home()
AGENTS_DIR = CODEX_HOME / "agents"
PROMPTS_DIR = CODEX_HOME / "prompts"
CONFIG_TOML = CODEX_HOME / "config.toml"
MODELS_JSON = CODEX_HOME / "models.json"

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_TEMPLATES_DIR = SCRIPT_DIR.parent / "templates" / "codex-agents"
PROMPT_TEMPLATES_DIR = SCRIPT_DIR.parent / "templates" / "codex-prompts"

AGENT_FILES = ["wakita-scout.toml", "wakita-builder.toml", "wakita-auditor.toml"]
PROMPT_FILES = [
    "wakita-subagent-create.md",
    "wakita-audit.md",
    "wakita-lock.md",
]

SANDBOX_MODES = {"read-only", "workspace-write", "danger-full-access"}


def err(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)


# ----------------------------- config.toml / models.json -----------------------------
def load_config_defaults(cfg_path: Path) -> dict:
    """Extract model / model_reasoning_effort defaults from ~/.codex/config.toml.

    Uses tomllib when available; otherwise a minimal regex fallback that only
    reads the two top-level string keys (Python 3.10 compatibility).
    """
    defaults = {"model": None, "model_reasoning_effort": None}
    if not cfg_path.is_file():
        return defaults
    text = cfg_path.read_text(encoding="utf-8-sig")
    if tomllib is not None:
        try:
            cfg = tomllib.loads(text)
            defaults["model"] = cfg.get("model")
            defaults["model_reasoning_effort"] = cfg.get("model_reasoning_effort")
            return defaults
        except tomllib.TOMLDecodeError:
            pass  # fall through to regex
    for key in defaults:
        m = re.search(rf"^\s*{re.escape(key)}\s*=\s*\"([^\"]+)\"", text, re.MULTILINE)
        if m:
            defaults[key] = m.group(1)
    return defaults


def load_model_slugs(models_path: Path) -> list[str] | None:
    """Return available model slugs from ~/.codex/models.json, or None if absent."""
    if not models_path.is_file():
        return None
    try:
        data = json.loads(models_path.read_text(encoding="utf-8-sig"))
        return [m.get("slug") for m in data.get("models", []) if m.get("slug")]
    except (json.JSONDecodeError, OSError):
        return None


# ----------------------------- template rendering -----------------------------
def render_text(raw: bytes, replacements: dict[str, str], source_name: str) -> bytes:
    """Replace top-level `key = "value"` lines with new values.

    Only lines at column 0 are touched (header lines in the TOML templates all
    start at column 0). When no replacements apply the input is preserved
    byte-for-byte (including line endings and the final newline).
    """
    text = raw.decode("utf-8")
    remaining = set(replacements)
    out = []
    for ln in text.splitlines(keepends=True):
        body = ln.rstrip("\r\n")
        matched = False
        for key, value in replacements.items():
            if re.match(rf"^{re.escape(key)}\s*=\s*\"[^\"]*\"", body):
                out.append(f'{key} = "{value}"' + ln[len(body):])
                remaining.discard(key)
                matched = True
                break
        if not matched:
            out.append(ln)
    if remaining:
        raise ValueError(
            f"{source_name}: keys not found for replacement: {', '.join(sorted(remaining))}"
        )
    return "".join(out).encode("utf-8")


def parse_toml_header(raw: bytes, source_name: str) -> dict | None:
    """Parse a TOML template header for sanity checks (name field)."""
    if tomllib is not None:
        try:
            return tomllib.loads(raw.decode("utf-8"))
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"{source_name}: invalid TOML: {e}") from e
    m = re.search(r'^name\s*=\s*"([^"]+)"', raw.decode("utf-8"), re.MULTILINE)
    return {"name": m.group(1)} if m else None


def extract_top_level(raw: bytes) -> dict:
    """Extract the effective model/reasoning/sandbox from a rendered agent file."""
    text = raw.decode("utf-8")
    out = {}
    for key in ("model", "model_reasoning_effort", "sandbox_mode"):
        m = re.search(rf"^{re.escape(key)}\s*=\s*\"([^\"]+)\"", text, re.MULTILINE)
        if m:
            out[key] = m.group(1)
    return out


def target_state(target_path: Path, content: bytes) -> str:
    """Read-only state of a target file vs the content we would write."""
    try:
        if not target_path.is_file():
            return "missing"
        return "identical" if target_path.read_bytes() == content else "will_update"
    except OSError:
        return "unreadable"


def write_file(target_path: Path, content: bytes) -> str:
    """Write one file with .bak backup; returns created|updated|skip."""
    if target_path.is_file():
        existing = target_path.read_bytes()
        if existing == content:
            return "skip"
        target_path.with_suffix(target_path.suffix + ".bak").write_bytes(existing)
        target_path.write_bytes(content)
        return "updated"
    target_path.write_bytes(content)
    return "created"


# ----------------------------- plan -----------------------------
def build_plan(args, config_defaults: dict, model_slugs) -> tuple[dict, list, list]:
    """Render all agents/prompts. Returns (meta, agent_plans, prompt_plans)."""
    # Explicit CLI overrides win; otherwise keep each template's per-agent
    # values (scout/builder: flash+high, auditor: pro+max). config.toml values
    # are only reported for display and never clobber template defaults.
    model = args.model
    reasoning = args.reasoning

    # ---- validate model against catalog ----
    if model and model_slugs and model not in model_slugs:
        err(f"model '{model}' not found in {MODELS_JSON}")
        err("Available models: " + ", ".join(model_slugs))
        sys.exit(1)

    # ---- validate sandbox ----
    if args.sandbox and args.sandbox not in SANDBOX_MODES:
        err(f"invalid --sandbox '{args.sandbox}'; expected one of {', '.join(sorted(SANDBOX_MODES))}")
        sys.exit(1)

    if reasoning and reasoning not in {"none", "minimal", "low", "medium", "high", "xhigh", "max"}:
        print(
            f"Warning: reasoning '{reasoning}' is unusual; expected one of "
            "none/minimal/low/medium/high/xhigh/max (model metadata is authoritative).",
            file=sys.stderr,
        )

    # ---- render agents ----
    agent_plans = []
    for af in AGENT_FILES:
        tpl = AGENT_TEMPLATES_DIR / af
        if not tpl.is_file():
            err(f"agent template not found: {tpl}")
            sys.exit(1)
        raw = tpl.read_bytes()
        header = parse_toml_header(raw, tpl.name)
        if header and header.get("name") != Path(af).stem:
            err(f"{tpl.name}: TOML 'name' field is '{header.get('name')}', expected '{Path(af).stem}'")
            sys.exit(1)
        replacements = {}
        if model:
            replacements["model"] = model
        if reasoning:
            replacements["model_reasoning_effort"] = reasoning
        if args.sandbox:
            replacements["sandbox_mode"] = args.sandbox
        try:
            content = render_text(raw, replacements, tpl.name)
        except ValueError as e:
            err(str(e))
            sys.exit(1)
        agent_plans.append({
            "file": af,
            "target": AGENTS_DIR / af,
            "content": content,
            "effective": extract_top_level(content),
        })

    # ---- render prompts ----
    prompt_plans = []
    if not args.no_prompts:
        for pf in PROMPT_FILES:
            tpl = PROMPT_TEMPLATES_DIR / pf
            if not tpl.is_file():
                err(f"prompt template not found: {tpl}")
                sys.exit(1)
            prompt_plans.append({"file": pf, "target": PROMPTS_DIR / pf, "content": tpl.read_bytes()})

    meta = {
        "codex_home": str(CODEX_HOME),
        "config_defaults": {k: v for k, v in config_defaults.items() if v is not None},
        "effective": {
            "model": model or "(template per-agent)",
            "model_reasoning_effort": reasoning or "(template per-agent)",
            "sandbox_mode": args.sandbox,
        },
        "prompts": not args.no_prompts,
    }

    # Warn when a template's model is not in the local catalog (the user can
    # pass --model to switch to a model their provider actually exposes).
    if model_slugs:
        for plan in agent_plans:
            m = re.search(r'^model\s*=\s*"([^"]+)"', plan["content"].decode("utf-8"), re.MULTILINE)
            if m and m.group(1) not in model_slugs:
                print(
                    f"Warning: {plan['file']} template model '{m.group(1)}' is not in "
                    f"{MODELS_JSON.name}; pass --model to use an available model.",
                    file=sys.stderr,
                )
    return meta, agent_plans, prompt_plans


# ----------------------------- main -----------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install wakita-governance roles as Codex custom agents (~/.codex/agents/) "
        "and the ZCode command equivalents as Codex prompts (~/.codex/prompts/).",
    )
    parser.add_argument("--model", default=None,
                        help="Model for all three agents (default: template value or ~/.codex/config.toml)")
    parser.add_argument("--reasoning", dest="reasoning", default=None,
                        help="model_reasoning_effort for all three agents (e.g. high/max; default: template/config)")
    parser.add_argument("--sandbox", default=None,
                        help="sandbox_mode for all three agents (read-only/workspace-write/danger-full-access)")
    parser.add_argument("--no-prompts", action="store_true",
                        help="Skip installing the Codex custom prompts (~/.codex/prompts/)")
    parser.add_argument("--json", action="store_true",
                        help="Print effective defaults as JSON and exit (no writes)")
    parser.add_argument("--list", action="store_true",
                        help="Print a human-readable plan and exit (no writes)")
    parser.add_argument("--apply", action="store_true",
                        help="Actually write files; without this flag only a dry-run plan is printed")
    args = parser.parse_args()

    config_defaults = load_config_defaults(CONFIG_TOML)
    model_slugs = load_model_slugs(MODELS_JSON)

    meta, agent_plans, prompt_plans = build_plan(args, config_defaults, model_slugs)

    if args.json:
        print(json.dumps({
            "codex_home": meta["codex_home"],
            "config_defaults": meta["config_defaults"],
            "effective": meta["effective"],
            "agents": [
                {"file": f["file"], **f["effective"]}
                for f in agent_plans
            ],
            "prompts": [f["file"] for f in prompt_plans],
            "models_json": str(MODELS_JSON) if model_slugs is not None else None,
        }, ensure_ascii=False, indent=2))
        return 0

    if args.list:
        print(f"Codex home: {meta['codex_home']}")
        print(f"Effective model: {meta['effective']['model']} / reasoning: "
              f"{meta['effective']['model_reasoning_effort']} / sandbox: "
              f"{meta['effective']['sandbox_mode'] or '(template per-agent)'}")
        print("Agents ->", AGENTS_DIR)
        for p in agent_plans:
            print(f"  {p['file']}: {target_state(p['target'], p['content'])}")
        if prompt_plans:
            print("Prompts ->", PROMPTS_DIR)
            for p in prompt_plans:
                print(f"  {p['file']}: {target_state(p['target'], p['content'])}")
        return 0

    # ---- dry-run guard ----
    if not args.apply:
        print(json.dumps({
            "dry_run": True,
            "codex_home": meta["codex_home"],
            "effective": meta["effective"],
            "agents": [
                {"file": p["file"], "target": str(p["target"]), "state": target_state(p["target"], p["content"])}
                for p in agent_plans
            ],
            "prompts": [
                {"file": p["file"], "target": str(p["target"]), "state": target_state(p["target"], p["content"])}
                for p in prompt_plans
            ],
            "note": "Re-run with --apply to actually write the files.",
        }, ensure_ascii=False, indent=2))
        return 0

    # ---- apply ----
    try:
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        if prompt_plans:
            PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        err(f"cannot create target dirs: {e}")
        return 1

    created, updated, skipped = [], [], []
    for p in agent_plans + prompt_plans:
        try:
            status = write_file(p["target"], p["content"])
        except OSError as e:
            err(f"failed to write {p['file']}: {e}")
            status = "failed"
        if status == "created":
            created.append(p["file"])
        elif status == "updated":
            updated.append(p["file"])
        elif status == "skip":
            skipped.append(p["file"])

    failed = [p["file"] for p in agent_plans + prompt_plans
              if not (p["file"] in created or p["file"] in updated or p["file"] in skipped)]
    if failed:
        err(f"Completed with errors on: {failed}")
        return 1

    print(json.dumps({
        "ok": True,
        "applied": True,
        "codex_home": meta["codex_home"],
        "effective": meta["effective"],
        "agents_dir": str(AGENTS_DIR),
        "prompts_dir": str(PROMPTS_DIR) if prompt_plans else None,
        "created_files": created,
        "updated_files": updated,
        "skipped_files": skipped,
        "restart_hint": (
            "新会话（或重启 Codex App / CLI）后可用 @wakita-scout / @wakita-builder / "
            "@wakita-auditor 调遣；CLI 中提示词以 /wakita-subagent-create、/wakita-audit、"
            "/wakita-lock 出现。"
        ),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
