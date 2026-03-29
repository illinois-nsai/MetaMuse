import json
from enum import Enum
from typing import List

from .design import Design
from .evaluation_info import EvaluationInfo
from .keyword_list import KeywordList


class EntryType(Enum):
    RSDICT = 0
    RSDICT_SF = 1


class Entry:
    def __init__(self, id: int, entry_type: EntryType):
        self.id: int = id
        self.entry_type: EntryType = entry_type
        self.hints: KeywordList = None
        self.design: Design = None
        self.code: str = None
        self.evaluation_info: EvaluationInfo = None
        self.fb_emb: List[float] = None

    def __str__(self):
        return f"(id={self.id}, type={self.entry_type.name})"

    def __repr__(self):
        return self.__str__()

    def to_dict(self, store_fb_emb: bool = True) -> dict:
        entry_dict = {
            "id": self.id,
            "type": self.entry_type.name,
            "hints": self.hints.to_str() if self.hints is not None else None,
            "design": self.design.to_dict() if self.design is not None else None,
            "code": self.code,
            "evaluation_info": self.evaluation_info.to_dict() if self.evaluation_info is not None else None,
            "fb_emb": self.fb_emb,
        }
        if not store_fb_emb:
            del entry_dict["fb_emb"]
        return entry_dict

    def to_jsonl(self, store_fb_emb: bool = True) -> str:
        return json.dumps(self.to_dict(store_fb_emb))
