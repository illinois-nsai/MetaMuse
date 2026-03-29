from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class Simulator(ABC):
    def __init__(self, name: str, code_folder: str):
        self.name = name
        self.code_folder = code_folder
        self.code_path: Optional[str] = None
        self.latency: float = 0.0

    @abstractmethod
    def simulate(self, code: str, code_id: str) -> Optional[float]:
        pass

    @abstractmethod
    def tune(self, code: str, code_id: str, fixed_default_param: bool = False):
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "code_folder": self.code_folder,
            "latency": self.latency,
        }


TuneResult = Tuple[Optional[float], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]
