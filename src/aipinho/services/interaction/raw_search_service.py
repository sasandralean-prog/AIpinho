from __future__ import annotations
from aipinho.schemas.interaction.raw_search_result import RawSearchResult
from aipinho.services.interaction.raw_viewer_service import RawViewerService
class RawSearchService:
    def search(self,raw_ref_id:str,query:str)->RawSearchResult:
        text=RawViewerService().viewer(raw_ref_id).sanitized_text; q=query.lower(); matches=[]
        for index,line in enumerate(text.splitlines(),start=1):
            if q and q in line.lower(): matches.append({"line":index,"text":line})
        return RawSearchResult(raw_ref_id=raw_ref_id,query=query,total=len(matches),matches=matches)
