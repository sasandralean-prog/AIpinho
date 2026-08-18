from __future__ import annotations


def generic_files_template(*, project_name: str, user_goal: str) -> dict[str, str]:
    return {
        "README.md": f"# {project_name}\n\nGenerated inside the governed AIpinho sandbox.\n\n## User goal\n\n{user_goal}\n",
        "notes.md": "This generic project was created because the request did not match a specialized template.\n",
    }
