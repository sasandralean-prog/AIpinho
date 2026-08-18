from __future__ import annotations


def static_web_template(*, project_name: str) -> dict[str, str]:
    return {
        "README.md": f"# {project_name}\n\nStatic web demo generated inside AIpinho sandbox.\n",
        "index.html": '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AIpinho Sandbox</title><link rel="stylesheet" href="style.css"></head><body><main><h1>AIpinho Sandbox</h1><p>Demo neon gerada em sandbox governado.</p><button id="pulse">Ativar brilho</button></main><script src="script.js"></script></body></html>\n',
        "style.css": 'body{margin:0;background:#05070d;color:#39ff14;font-family:system-ui,sans-serif}main{min-height:100vh;display:grid;place-content:center;text-align:center}button{border:1px solid #22d3ee;background:#05070d;color:#22d3ee;border-radius:999px;padding:12px 20px}body.glow{box-shadow:inset 0 0 80px #ff2bd6}\n',
        "script.js": 'document.getElementById("pulse")?.addEventListener("click",()=>document.body.classList.toggle("glow"));\n',
    }
