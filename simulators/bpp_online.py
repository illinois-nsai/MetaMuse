import os

from simulators.bpp_core import BPPEval, BPPEvalConfig
from simulators.base import Simulator
from simulators.sim_utils import (
    build_configspace,
    update_code,
    simulate_code,
    tune_code,
)


class BPPOnlineSimulator(Simulator):
    def __init__(
        self,
        trace_path: str = None,
        trace_folder: str = None,
        code_folder: str = None,
        tune_runs: int = 20,
        tune_int_upper: int = None,
        timeout_seconds: int = 5,
    ):
        if trace_path is None and trace_folder is None:
            raise ValueError("Either trace_path or trace_folder must be provided")
        if trace_path is not None and trace_folder is not None:
            raise ValueError("Only one of trace_path or trace_folder can be provided")
        if code_folder is None:
            raise ValueError("code_folder must be provided")
        super().__init__(name="BPPOnline", code_folder=code_folder)
        if trace_folder is not None:
            if not os.path.exists(trace_folder):
                raise FileNotFoundError(trace_folder)
            trace_files = sorted(os.listdir(trace_folder))
            self.trace_paths = [os.path.join(trace_folder, t) for t in trace_files]
        else:
            self.trace_paths = [trace_path]
        self.trace_configs = [BPPEvalConfig(trace_path=p) for p in self.trace_paths]
        self.tune_runs = tune_runs
        self.tune_int_upper = tune_int_upper
        self.timeout_seconds = timeout_seconds
        if self.tune_int_upper is None:
            upper = 1
            for cfg in self.trace_configs:
                upper = max(upper, cfg.instance["capacity"], cfg.instance["num_items"])
            self.tune_int_upper = upper

    def _run(self, code: str):
        policy_module = {}
        exec(code, policy_module)
        scores = []
        for cfg in self.trace_configs:
            eval = BPPEval(config=cfg, policy_module=policy_module)
            scores.append(eval.simulate() * 100)
        if not scores:
            return None
        return round(sum(scores) / len(scores), 4)

    def _reset(self):
        # No simulator state to reset yet; keep for compatibility.
        return None

    def simulate(self, code: str, code_id: str):
        return simulate_code(self, code, code_id, self._run, self.timeout_seconds, on_error=self._reset)

    def tune(self, code: str, code_id: str, fixed_default_param: bool = False):
        return tune_code(
            self,
            code,
            code_id,
            fixed_default_param,
            lambda c, fixed: build_configspace(c, fixed, self.tune_int_upper),
            update_code,
            self._run,
            self.timeout_seconds,
            self.tune_runs,
        )


def build_test_simulators(
    test_folder: str,
    trace_filter=None,
    code_folder: str = None,
    tune_runs: int = 1,
    tune_int_upper: int = None,
    timeout_seconds: int = 5,
):
    if not os.path.exists(test_folder):
        raise FileNotFoundError(test_folder)
    if code_folder is None:
        code_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "log", "code")
        code_folder = os.path.abspath(code_folder)

    test_trace_list = sorted(os.listdir(test_folder))
    if trace_filter is not None:
        test_trace_list = [t for t in test_trace_list if not trace_filter(t)]

    return [
        BPPOnlineSimulator(
            trace_path=os.path.join(test_folder, trace_file),
            code_folder=code_folder,
            tune_runs=tune_runs,
            tune_int_upper=tune_int_upper,
            timeout_seconds=timeout_seconds,
        )
        for trace_file in test_trace_list
    ]
