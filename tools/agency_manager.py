#!/usr/bin/env python3
r"""
Agency-Agents Manager & Antigravity Converter for E:\.agents
Converts msitarzewski/agency-agents personas into Antigravity SKILL.md format,
maintains a searchable catalog, and registers skills in Antigravity / Claude Code / Gemini CLI.
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
AGENCY_SRC_DIR = ROOT_DIR / "agents" / "agency"
AGENCY_SKILLS_DIR = ROOT_DIR / "agency-skills"
CATALOG_FILE = AGENCY_SRC_DIR / "catalog.json"


def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def yaml_quote(val: str) -> str:
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


def parse_agent_md(md_path: Path):
    content = md_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    fm_end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            fm_end = idx
            break
    if fm_end is None:
        return None

    fm_lines = lines[1:fm_end]
    body = "\n".join(lines[fm_end + 1 :]).lstrip("\n")

    fields = {}
    current_key = None
    for line in fm_lines:
        m = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if m:
            current_key = m.group(1)
            fields[current_key] = m.group(2).strip()
        elif current_key and re.match(r"^\s+\S", line):
            fields[current_key] = (fields[current_key] + " " + line.strip()).strip()

    for k, v in list(fields.items()):
        if len(v) >= 2 and v.startswith('"') and v.endswith('"'):
            v = v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        elif len(v) >= 2 and v.startswith("'") and v.endswith("'"):
            v = v[1:-1].replace("''", "'")
        fields[k] = v

    name = fields.get("name", "").strip()
    description = fields.get("description", "").strip()
    if not name or not description:
        return None

    slug = slugify(name)
    skill_slug = f"agency-{slug}"
    return {
        "name": name,
        "slug": slug,
        "skill_name": skill_slug,
        "description": description,
        "color": fields.get("color", ""),
        "emoji": fields.get("emoji", "🎭"),
        "vibe": fields.get("vibe", ""),
        "body": body,
        "stem": md_path.stem,
    }


def load_divisions():
    div_file = AGENCY_SRC_DIR / "divisions.json"
    if not div_file.exists():
        raise FileNotFoundError(f"Missing divisions.json at {div_file}")
    data = json.loads(div_file.read_text(encoding="utf-8"))
    return data.get("divisions", {})


def convert_all() -> dict:
    divisions = load_divisions()
    AGENCY_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    catalog = {
        "source_repo": "https://github.com/msitarzewski/agency-agents",
        "total_agents": 0,
        "divisions": {},
        "agents": [],
    }

    for div_key, div_meta in divisions.items():
        div_dir = AGENCY_SRC_DIR / div_key
        if not div_dir.exists():
            continue

        div_agents = []
        for md_file in sorted(div_dir.rglob("*.md")):
            parsed = parse_agent_md(md_file)
            if not parsed:
                continue

            skill_dir = AGENCY_SKILLS_DIR / parsed["skill_name"]
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_file = skill_dir / "SKILL.md"

            skill_content = (
                f"---\n"
                f"name: {yaml_quote(parsed['skill_name'])}\n"
                f"description: {yaml_quote(parsed['description'])}\n"
                f"---\n"
                f"{parsed['body']}\n"
            )
            skill_file.write_text(skill_content, encoding="utf-8")

            entry = {
                "name": parsed["name"],
                "slug": parsed["slug"],
                "skill_name": parsed["skill_name"],
                "division": div_key,
                "division_label": div_meta.get("label", div_key),
                "description": parsed["description"],
                "emoji": parsed["emoji"],
                "vibe": parsed["vibe"],
                "color": parsed["color"],
                "stem": parsed["stem"],
                "source_path": str(md_file.relative_to(ROOT_DIR)).replace("\\", "/"),
                "skill_path": str(skill_file.relative_to(ROOT_DIR)).replace("\\", "/"),
            }
            div_agents.append(entry)
            catalog["agents"].append(entry)

        catalog["divisions"][div_key] = {
            "label": div_meta.get("label", div_key),
            "icon": div_meta.get("icon", ""),
            "color": div_meta.get("color", ""),
            "count": len(div_agents),
            "skills": [a["skill_name"] for a in div_agents],
        }

    catalog["total_agents"] = len(catalog["agents"])
    CATALOG_FILE.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    return catalog


def update_skills_json(json_path: Path, include_only=None):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"entries": []}
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            data = {"entries": []}

    entries = data.get("entries", [])
    target_path_str = str(AGENCY_SKILLS_DIR.resolve())

    new_entry = {"path": target_path_str}
    if include_only:
        new_entry["include_only"] = include_only

    updated = False
    for idx, entry in enumerate(entries):
        if isinstance(entry, dict) and "path" in entry:
            try:
                if Path(entry["path"]).resolve() == AGENCY_SKILLS_DIR.resolve():
                    entries[idx] = new_entry
                    updated = True
                    break
            except Exception:
                pass

    if not updated:
        entries.append(new_entry)

    data["entries"] = entries
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def install_all(filter_divisions=None):
    if not CATALOG_FILE.exists():
        catalog = convert_all()
    else:
        catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))

    include_only = None
    if filter_divisions:
        include_only = []
        for d in filter_divisions:
            d = d.strip()
            if d in catalog["divisions"]:
                include_only.extend(catalog["divisions"][d]["skills"])

    # 1. Register in workspace E:\.agents\skills.json
    ws_skills_json = ROOT_DIR / "skills.json"
    update_skills_json(ws_skills_json, include_only=include_only)
    print(f"[OK] Registered E:\\.agents\\agency-skills in {ws_skills_json}")

    # 2. Register in global ~/.gemini/config/skills.json
    global_skills_json = Path.home() / ".gemini" / "config" / "skills.json"
    update_skills_json(global_skills_json, include_only=include_only)
    print(f"[OK] Registered E:\\.agents\\agency-skills in {global_skills_json}")

    # 3. Install to Gemini CLI (~/.gemini/agents/)
    gemini_agents_dir = Path.home() / ".gemini" / "agents"
    gemini_agents_dir.mkdir(parents=True, exist_ok=True)
    g_count = 0
    for agent in catalog["agents"]:
        if filter_divisions and agent["division"] not in filter_divisions:
            continue
        src_md = ROOT_DIR / agent["source_path"]
        parsed = parse_agent_md(src_md)
        if parsed:
            out_md = gemini_agents_dir / f"{parsed['slug']}.md"
            out_md.write_text(
                f"---\nname: {yaml_quote(parsed['slug'])}\ndescription: {yaml_quote(parsed['description'])}\n---\n{parsed['body']}\n",
                encoding="utf-8",
            )
            g_count += 1
    print(f"[OK] Installed {g_count} agents to Gemini CLI ({gemini_agents_dir})")

    # 4. Install to Claude Code (~/.claude/agents/) if ~/.claude exists
    claude_dir = Path.home() / ".claude"
    if claude_dir.exists():
        claude_agents_dir = claude_dir / "agents"
        claude_agents_dir.mkdir(parents=True, exist_ok=True)
        c_count = 0
        for agent in catalog["agents"]:
            if filter_divisions and agent["division"] not in filter_divisions:
                continue
            src_md = ROOT_DIR / agent["source_path"]
            shutil.copy2(src_md, claude_agents_dir / src_md.name)
            c_count += 1
        print(f"[OK] Installed {c_count} agents to Claude Code ({claude_agents_dir})")


def main():
    parser = argparse.ArgumentParser(description="Agency-Agents Manager for E:\\.agents")
    parser.add_argument("--convert", action="store_true", help="Convert all agency agents to Antigravity skills")
    parser.add_argument("--install", action="store_true", help="Register converted skills into Antigravity, Gemini CLI, and Claude Code")
    parser.add_argument("--filter-divisions", type=str, default="", help="Comma-separated list of divisions to enable (default: all)")
    parser.add_argument("--list-divisions", action="store_true", help="List all 18 divisions and agent counts")
    parser.add_argument("--list-agents", action="store_true", help="List agents (optionally filtered by --division)")
    parser.add_argument("--division", type=str, default="", help="Filter --list-agents by division slug")
    parser.add_argument("--search", type=str, default="", help="Search agents by keyword in name/description/vibe")
    args = parser.parse_args()

    if args.convert or not CATALOG_FILE.exists():
        catalog = convert_all()
        print(f"[OK] Converted {catalog['total_agents']} agents across {len(catalog['divisions'])} divisions into {AGENCY_SKILLS_DIR}")
    else:
        catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))

    if args.install:
        divs = [d.strip() for d in args.filter_divisions.split(",") if d.strip()] if args.filter_divisions else None
        install_all(filter_divisions=divs)

    if args.list_divisions:
        print(f"\n{'Division Slug':<22} | {'Label':<22} | {'Count':<6}")
        print("-" * 56)
        for k, v in catalog["divisions"].items():
            print(f"{k:<22} | {v['label']:<22} | {v['count']:<6}")
        print("-" * 56)
        print(f"Total: {catalog['total_agents']} agents\n")

    if args.list_agents:
        target_div = args.division.strip().lower()
        for a in catalog["agents"]:
            if target_div and a["division"] != target_div:
                continue
            print(f"{a['emoji']} {a['skill_name']:<42} [{a['division']}] - {a['name']}")

    if args.search:
        q = args.search.lower()
        matches = [
            a for a in catalog["agents"]
            if q in a["name"].lower()
            or q in a["description"].lower()
            or q in a["vibe"].lower()
            or q in a["skill_name"].lower()
            or q in a["division"].lower()
        ]
        print(f"\nFound {len(matches)} matching agents for '{args.search}':")
        for a in matches:
            print(f"  • {a['emoji']} {a['skill_name']} ({a['name']} | {a['division']})")
            print(f"    {a['description']}")


if __name__ == "__main__":
    main()
