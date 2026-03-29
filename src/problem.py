import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional

from .utils import read_text


def _render_template(template: str, values: Dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"[[{key}]]", value)
    return rendered


def _default_design_text(design_dict: Dict[str, Any]) -> str:
    if not design_dict:
        return ""
    lines = []
    for key, value in design_dict.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


@dataclass
class ProblemSpec:
    name: str
    map_prompt: str
    design_prompt: str
    code_prompt: str
    design_required_keys: Iterable[str] = field(default_factory=tuple)
    code_extension: Optional[str] = ".py"
    metric_name: str = "score"
    design_text_builder: Optional[Callable[[Dict[str, Any]], str]] = None
    design_field_formatter: Optional[Callable[[str, Any], str]] = None
    validate_prompts: bool = True

    def __post_init__(self):
        if self.validate_prompts:
            self.validate()

    @classmethod
    def from_paths(
        cls,
        name: str,
        map_prompt_path: str,
        design_prompt_path: str,
        code_prompt_path: str,
        *,
        design_required_keys: Optional[Iterable[str]] = None,
        metric_name: str = "score",
        code_extension: Optional[str] = ".py",
        design_text_builder: Optional[Callable[[Dict[str, Any]], str]] = None,
        design_field_formatter: Optional[Callable[[str, Any], str]] = None,
        validate_prompts: bool = True,
    ):
        return cls(
            name=name,
            map_prompt=read_text(map_prompt_path).strip(),
            design_prompt=read_text(design_prompt_path).strip(),
            code_prompt=read_text(code_prompt_path).strip(),
            design_required_keys=design_required_keys or (),
            metric_name=metric_name,
            code_extension=code_extension,
            design_text_builder=design_text_builder,
            design_field_formatter=design_field_formatter,
            validate_prompts=validate_prompts,
        )

    @classmethod
    def from_dir(
        cls,
        name: str,
        prompt_dir: str,
        map_filename: str = "map_prompt.txt",
        design_filename: str = "design_prompt.txt",
        code_filename: str = "code_prompt.txt",
        *,
        design_required_keys: Optional[Iterable[str]] = None,
        metric_name: str = "score",
        code_extension: Optional[str] = ".py",
        design_text_builder: Optional[Callable[[Dict[str, Any]], str]] = None,
        design_field_formatter: Optional[Callable[[str, Any], str]] = None,
        validate_prompts: bool = True,
    ):
        return cls.from_paths(
            name=name,
            map_prompt_path=os.path.join(prompt_dir, map_filename),
            design_prompt_path=os.path.join(prompt_dir, design_filename),
            code_prompt_path=os.path.join(prompt_dir, code_filename),
            design_required_keys=design_required_keys,
            metric_name=metric_name,
            code_extension=code_extension,
            design_text_builder=design_text_builder,
            design_field_formatter=design_field_formatter,
            validate_prompts=validate_prompts,
        )

    def render_map_prompt(self, word: str) -> str:
        return _render_template(self.map_prompt, {"word": word})

    def render_design_prompt(self, hints: str) -> str:
        return _render_template(self.design_prompt, {"hints": hints})

    def format_design_text(self, design_dict: Dict[str, Any]) -> str:
        if self.design_text_builder is not None:
            return self.design_text_builder(design_dict)
        return _default_design_text(design_dict)

    def format_design_field(self, key: str, value: Any) -> str:
        if self.design_field_formatter is not None:
            return self.design_field_formatter(key, value)
        return "" if value is None else str(value)

    def render_code_prompt(self, design_dict: Dict[str, Any]) -> str:
        replacements = {"design": self.format_design_text(design_dict)}
        for key, value in design_dict.items():
            replacements[key] = self.format_design_field(key, value)
        return _render_template(self.code_prompt, replacements)

    def validate(self):
        missing = []
        if "[[word]]" not in self.map_prompt:
            missing.append("map_prompt: [[word]]")
        if "[[hints]]" not in self.design_prompt:
            missing.append("design_prompt: [[hints]]")
        if "[[design]]" not in self.code_prompt:
            missing.append("code_prompt: [[design]]")
        for key in self.design_required_keys:
            if f"[[{key}]]" not in self.code_prompt:
                missing.append(f"code_prompt: [[{key}]]")
        if missing:
            raise ValueError(f"ProblemSpec prompt placeholders missing: {', '.join(missing)}")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "design_required_keys": list(self.design_required_keys),
            "metric_name": self.metric_name,
            "code_extension": self.code_extension,
        }
