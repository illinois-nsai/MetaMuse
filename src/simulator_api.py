from typing import Any, Dict, Optional, Protocol, Tuple

TuneResult = Tuple[Optional[float], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]


class SimulatorLike(Protocol):
    name: str
    code_folder: str
    code_path: Optional[str]
    latency: float

    def simulate(self, code: str, code_id: str) -> Optional[float]:
        ...

    def tune(self, code: str, code_id: str, fixed_default_param: bool = False) -> Optional[TuneResult]:
        ...

    def to_dict(self) -> Dict[str, Any]:
        ...
