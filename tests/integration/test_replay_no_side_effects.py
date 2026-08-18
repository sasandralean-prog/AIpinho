import ast
from aipinho.core.paths import PATHS

def test_replay_and_regression_services_have_no_execution_imports():
    forbidden_imports={"subprocess","requests","httpx","git","playwright","selenium"}
    roots=[PATHS.package_root/"services"/"replay", PATHS.package_root/"services"/"regression"]
    for root in roots:
        for path in root.rglob("*.py"):
            tree=ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node,(ast.Import,ast.ImportFrom)):
                    names={alias.name.split(".")[0] for alias in node.names}
                    assert not names & forbidden_imports, (path,names)
