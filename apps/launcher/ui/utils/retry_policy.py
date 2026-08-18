def next_backoff(attempt:int, schedule:tuple[int,...]=(1,2,5,10,30))->int:
    return schedule[min(max(attempt,0),len(schedule)-1)]
