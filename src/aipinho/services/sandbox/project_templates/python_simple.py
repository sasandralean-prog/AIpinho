from __future__ import annotations


def python_simple_app_template(*, project_name: str) -> dict[str, str]:
    return {
        "README.md": f"# {project_name}\n\nSimple Python CLI generated inside AIpinho sandbox.\n",
        "main.py": 'from pathlib import Path\nimport sys\n\n\ndef list_by_extension(root: str) -> dict[str, int]:\n    counts: dict[str, int] = {}\n    for path in Path(root).rglob("*"):\n        if path.is_file():\n            counts[path.suffix.lower() or "<none>"] = counts.get(path.suffix.lower() or "<none>", 0) + 1\n    return counts\n\n\nif __name__ == "__main__":\n    target = sys.argv[1] if len(sys.argv) > 1 else "."\n    for ext, count in sorted(list_by_extension(target).items()):\n        print(f"{ext}: {count}")\n',
        "requirements.txt": "",
        "tests/test_basic.py": 'from main import list_by_extension\n\n\ndef test_list_by_extension(tmp_path):\n    (tmp_path / "a.txt").write_text("a")\n    assert list_by_extension(str(tmp_path))[".txt"] == 1\n',
    }
