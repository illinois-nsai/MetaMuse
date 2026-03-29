import json
import re
from abc import ABC, abstractmethod
from typing import Iterable, Optional

import regex

from .simulator_api import SimulatorLike


class BaseParser(ABC):
    def __init__(self):
        self.error = ""
        self.name = ""

    @abstractmethod
    def parse(self, input: str):
        pass

    def to_dict(self) -> dict:
        return {"name": self.name}

    def print_error(self) -> str:
        return f"Parser-{self.name} Error: {self.error}"


class MapParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.name = "Map"

    def parse(self, input: str):
        if input is None:
            self.error = "[Invalid raw LLM response]"
            return None
        lines = input.strip().split("\n")
        nonempty_lines = [l.strip() for l in lines if len(l.strip()) > 0]
        if not nonempty_lines:
            self.error = "[No Answer found]"
            return None
        return nonempty_lines[-1]


class JsonParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.name = "Json"

    def parse(self, input: str):
        self.error = ""
        if input is None:
            self.error = "[Invalid raw LLM response]"
            return None
        try:
            json_pattern = r"\{(?:[^{}]|(?R))*\}"
            json_match = regex.search(json_pattern, input)
            if json_match is None:
                raise TypeError
            json_str = json_match.group()
            extracted_json = json.loads(json_str)
            return extracted_json
        except Exception:
            self.error = "[No JSON found]"
            return None


class DesignJsonParser(JsonParser):
    def __init__(self, required_keys: Optional[Iterable[str]] = None):
        super().__init__()
        self.name = "DesignJson"
        self.required_keys = list(required_keys or [])

    def parse(self, input: str):
        extracted_json = super().parse(input)
        if extracted_json is None:
            return None
        missing = []
        for key in self.required_keys:
            if key not in extracted_json:
                missing.append(key)
        if missing:
            self.error = "[Invalid JSON format] missing: " + ", ".join(missing)
            return None
        return extracted_json


class PythonParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.name = "Python"

    def parse(self, input: str):
        self.error = ""
        if input is None:
            self.error = "[Invalid raw LLM response]"
            return None
        match = re.search(r"```python(.*?)```", input, re.DOTALL)
        if match:
            code = match.group(1).strip()
            if code:
                return code
        self.error = "[No Python code found]"
        return None


class CodeParser(PythonParser):
    def __init__(self, unique_simulator: SimulatorLike):
        super().__init__()
        self.name = unique_simulator.name
        self.simulator = unique_simulator
        self.code_id = None

    def set_code_id(self, code_id):
        self.code_id = code_id

    def parse(self, input: str):
        if self.code_id is None:
            raise ValueError("code_id must be set before parsing")
        code = super().parse(input)
        if code is None:
            return None

        default_score = self.simulator.simulate(code, self.code_id)
        if default_score is None:
            self.error = "[Invalid Code]"
            return None

        tune_result = self.simulator.tune(code, self.code_id, False)
        if tune_result is None:
            return default_score, default_score, None, None

        tuned_mr, default_params, tuned_params = tune_result
        if tuned_mr is None or tuned_mr > default_score:
            tuned_mr = default_score
            tuned_params = default_params
        return default_score, tuned_mr, default_params, tuned_params

    def to_dict(self) -> dict:
        my_dict = super().to_dict()
        my_dict.update({"simulator": self.simulator.to_dict()})
        return my_dict
