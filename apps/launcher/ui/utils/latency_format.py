def format_latency(ms:int|None)->str:
    return "latencia desconhecida" if ms is None else f"{ms} ms"
