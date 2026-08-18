from __future__ import annotations
from aipinho.schemas.ux.ux_progress_indicator import UXProgressIndicator
class UXProgressService:
    def progress(self,item_id:str,label:str,current:int,total:int,state:str="running")->UXProgressIndicator:
        percent=0.0 if total<=0 else min(100.0,max(0.0,current*100.0/total))
        if current>=total and total>0: state="completed"
        return UXProgressIndicator(item_id=item_id,label=label,current=current,total=total,state=state,percent=percent)
