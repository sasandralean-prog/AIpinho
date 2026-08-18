from pathlib import Path
import ast
from aipinho.core.paths import PATHS

def test_maintenance_services_have_no_execution_imports_or_calls():
    root=PATHS.package_root/"services"/"maintenance"
    forbidden_imports={"subprocess","git","requests","httpx","selenium","playwright"}
    forbidden_calls={"system","popen","run_shell","apply_patch","write_config","write_policy","write_memory"}
    for path in root.rglob("*.py"):
        tree=ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names={alias.name.split(".")[0] for alias in node.names}
                assert not names & forbidden_imports, (path,names)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                assert node.func.attr.lower() not in forbidden_calls, (path,node.func.attr)
