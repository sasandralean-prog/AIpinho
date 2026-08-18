def percent(current:int,total:int)->float:
    return 0.0 if total<=0 else min(100.0,max(0.0,current*100.0/total))
def format_progress(current:int,total:int)->str:
    return f"{percent(current,total):.0f}%"
