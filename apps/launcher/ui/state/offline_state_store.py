from __future__ import annotations
from dataclasses import dataclass, field
@dataclass
class OfflineStateStore:
    values: dict[str, object] = field(default_factory=dict)
    def set(self,key:str,value:object)->None: self.values[key]=value
    def get(self,key:str,default:object=None)->object: return self.values.get(key,default)
    def snapshot(self)->dict[str,object]: return dict(self.values)
