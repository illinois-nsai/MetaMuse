class Design:
    def __init__(self, design_dict: dict):
        if not isinstance(design_dict, dict):
            raise TypeError("design_dict must be a dict")
        self.data = design_dict

    def to_str(self) -> str:
        if not self.data:
            return ""
        lines = []
        for key, value in self.data.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return dict(self.data)
