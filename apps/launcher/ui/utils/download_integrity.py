import hashlib
def sha256_bytes(content:bytes)->str: return hashlib.sha256(content).hexdigest()
def verify_sha256(content:bytes,expected:str|None)->bool: return bool(expected) and sha256_bytes(content).lower()==expected.lower()
