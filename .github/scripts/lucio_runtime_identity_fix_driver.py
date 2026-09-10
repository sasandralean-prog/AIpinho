from __future__ import annotations

import runpy
from pathlib import Path

script = Path(__file__).with_name("lucio_runtime_identity_fix.py")
text = script.read_text(encoding="utf-8")
old = '''    text = replace_once(\n        text,\n        ''' + "'''" + '''                "requires_task": False,\\n                "readonly": True,\\n''' + "'''" + ''',\n        ''' + "'''" + '''                "requires_task": True,\\n                "readonly": True,\\n''' + "'''" + ''',\n        label="timeout preserves task requirement",\n    )\n'''
new = '''    timeout_start = text.index("    def _timeout_blocked_response(")\n    timeout_end = text.find("\\n    def ", timeout_start + 5)\n    if timeout_end < 0:\n        timeout_end = len(text)\n    timeout_block = text[timeout_start:timeout_end]\n    timeout_block = replace_once(\n        timeout_block,\n        ''' + "'''" + '''                "requires_task": False,\\n                "readonly": True,\\n''' + "'''" + ''',\n        ''' + "'''" + '''                "requires_task": True,\\n                "readonly": True,\\n''' + "'''" + ''',\n        label="timeout preserves task requirement",\n    )\n    text = text[:timeout_start] + timeout_block + text[timeout_end:]\n'''
if text.count(old) != 1:
    raise SystemExit(f"driver expected one timeout patch block, found {text.count(old)}")
script.write_text(text.replace(old, new, 1), encoding="utf-8")
runpy.run_path(str(script), run_name="__main__")
