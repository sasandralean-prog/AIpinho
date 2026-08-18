from pathlib import Path
def can_open_without_execute(path:str)->bool:
    return Path(path).suffix.lower() not in {".exe",".dll",".bat",".cmd",".ps1",".sh",".msi"}
