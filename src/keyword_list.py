from typing import List


class KeywordList:
    def __init__(self, keyword_str: str):
        self.keyword_list: List[str] = [
            k.strip().lower() for k in keyword_str.split(",") if len(k.strip()) > 0
        ]

    def __add__(self, other):
        if not isinstance(other, KeywordList):
            raise TypeError(f"KeywordList cannot support addition with type {type(other)}")
        return KeywordList(self.to_str() + "," + other.to_str())

    def to_str(self, need_sort: bool = False):
        if need_sort:
            return ", ".join(sorted([k.lower() for k in self.keyword_list]))
        return ", ".join(self.keyword_list)
