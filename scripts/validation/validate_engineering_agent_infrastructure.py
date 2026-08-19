from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_SKILLS = {
    "aipinho-wave",
    "aipinho-firetest5",
    "aipinho-truth-audit",
    "aipinho-context-update",
    "aipinho-handoff",
    "aipinho-git-wave",
}

REQUIRED_AGENT_PROFILES = {
    "aipinho-planner.agent.md",
    "aipinho-engineer.agent.md",
    "aipinho-reviewer.agent.md",
}

REQUIRED_ENGINEERING_DOCS = {
    "README.md",
    "PLATFORM_MATRIX.md",
    "GIT_WORKFLOW.md",
    "LOCAL_EXECUTION_OVERLAY.md",
    "VALIDATION_AUTHORITY.md",
    "CODEX_SETUP.md",
    "DEVIN_SETUP.md",
    "REPLIT_SETUP.md",
    "VSCODE_SETUP.md",
}

FORBIDDEN_INFRA_PATHS = {
    ".devin",
    ".replit",
    ".github/skills",
    ".github/copilot-instructions.md",
}

SECRET_OR_LOCAL_PATTERNS = (
    re.compile(r"(^|/)\.env(\.|$)"),
    re.compile(r"\.gguf$", re.IGNORECASE),
    re.compile(r"(^|/)(payload_refs|task_runs|sessions)/"),
    re.compile(r"^(data|runtime)/"),
)

INFRA_PREFIXES = (
    ".agents/",
    ".github/agents/",
    "docs/engineering_agents/",
    "scripts/validation/validate_engineering_agent_infrastructure.py",
    "tests/unit/test_engineering_agent_infrastructure.py",
    "AGENTS.md",
    "replit.md",
)


def _frontmatter_fields(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def _markdown_links(text: str) -> list[str]:
    links = []
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        links.append(target.split("#", 1)[0])
    return links


def _tracked_files(root: Path) -> list[str]:
    git = root / ".git"
    if not git.exists():
        return []
    import subprocess

    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def validate(root: Path) -> list[str]:
    failures: list[str] = []

    if not (root / "AGENTS.md").is_file():
        failures.append("AGENTS.md missing")

    agents_text = (root / "AGENTS.md").read_text(encoding="utf-8") if (root / "AGENTS.md").exists() else ""
    for required in ("working ON AIpinho", "config/agents/", "src/aipinho/services/agents/"):
        if required not in agents_text:
            failures.append(f"AGENTS.md missing required namespace text: {required}")

    skills_root = root / ".agents" / "skills"
    if not skills_root.is_dir():
        failures.append(".agents/skills missing")
    else:
        found = {path.parent.name for path in skills_root.glob("*/SKILL.md")}
        if found != REQUIRED_SKILLS:
            failures.append(f"skill set mismatch: expected {sorted(REQUIRED_SKILLS)}, found {sorted(found)}")
        seen_names: set[str] = set()
        for skill_file in skills_root.glob("*/SKILL.md"):
            fields = _frontmatter_fields(skill_file.read_text(encoding="utf-8"))
            name = fields.get("name")
            description = fields.get("description")
            if not name or not description:
                failures.append(f"{skill_file.relative_to(root)} missing name/description frontmatter")
            if name in seen_names:
                failures.append(f"duplicate skill name: {name}")
            if name:
                seen_names.add(name)

    replit = root / "replit.md"
    if not replit.is_file():
        failures.append("replit.md missing")
    else:
        text = replit.read_text(encoding="utf-8")
        if "AGENTS.md is canonical" not in text or "config/agents/" not in text:
            failures.append("replit.md does not point to AGENTS.md and namespace distinction")

    github_agents = root / ".github" / "agents"
    if not github_agents.is_dir():
        failures.append(".github/agents missing")
    else:
        found_agents = {path.name for path in github_agents.glob("*.agent.md")}
        if found_agents != REQUIRED_AGENT_PROFILES:
            failures.append(f"agent profile set mismatch: expected {sorted(REQUIRED_AGENT_PROFILES)}, found {sorted(found_agents)}")
        for profile in github_agents.glob("*.agent.md"):
            fields = _frontmatter_fields(profile.read_text(encoding="utf-8"))
            if not fields.get("description"):
                failures.append(f"{profile.relative_to(root)} missing description frontmatter")

    docs_root = root / "docs" / "engineering_agents"
    if not docs_root.is_dir():
        failures.append("docs/engineering_agents missing")
    else:
        found_docs = {path.name for path in docs_root.glob("*.md")}
        missing_docs = REQUIRED_ENGINEERING_DOCS - found_docs
        if missing_docs:
            failures.append(f"engineering docs missing: {sorted(missing_docs)}")

    for rel in FORBIDDEN_INFRA_PATHS:
        if (root / rel).exists():
            failures.append(f"forbidden speculative infrastructure exists: {rel}")

    docs_to_check = [root / "AGENTS.md", root / "replit.md", *docs_root.glob("*.md"), *github_agents.glob("*.agent.md")]
    for doc in docs_to_check:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")
        if "docs/CONTEXT" in text:
            failures.append(f"{doc.relative_to(root)} references retired docs/CONTEXT path")
        for link in _markdown_links(text):
            target = (doc.parent / link).resolve() if not link.startswith("/") else root / link.lstrip("/")
            try:
                target.relative_to(root.resolve())
            except ValueError:
                continue
            if not target.exists():
                failures.append(f"{doc.relative_to(root)} has missing link target: {link}")

    authority = root / "DOCUMENT_AUTHORITY.md"
    if authority.exists():
        text = authority.read_text(encoding="utf-8")
        for required in ("AGENTS.md", ".agents/skills/", "docs/engineering_agents/"):
            if required not in text:
                failures.append(f"DOCUMENT_AUTHORITY.md missing implemented engineering authority: {required}")

    tracked = [
        rel
        for rel in _tracked_files(root)
        if rel in INFRA_PREFIXES or any(rel.startswith(prefix) for prefix in INFRA_PREFIXES)
    ]
    for rel in tracked:
        normalized = rel.replace("\\", "/")
        if any(pattern.search(normalized) for pattern in SECRET_OR_LOCAL_PATTERNS):
            failures.append(f"tracked local-overlay candidate: {normalized}")

    return failures


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    failures = validate(root.resolve())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("engineering agent infrastructure validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
