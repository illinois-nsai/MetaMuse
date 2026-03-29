from typing import Dict, Optional


class EvaluationInfo:
    def __init__(
        self,
        default_score: float,
        tuned_score: float,
        default_params: Dict,
        tuned_params: Dict,
        metric_name: str = "score",
        extra_metrics: Optional[Dict] = None,
    ):
        self.metric_name = metric_name
        self.default_score = default_score
        self.default_params = default_params
        self.tuned_score = tuned_score
        self.tuned_params = tuned_params
        self.extra_metrics = extra_metrics or {}

    def to_dict(self):
        return {
            "metric_name": self.metric_name,
            "default_score": self.default_score,
            "tuned_score": self.tuned_score,
            "default_params": self.default_params,
            "tuned_params": self.tuned_params,
            "extra_metrics": self.extra_metrics,
        }
