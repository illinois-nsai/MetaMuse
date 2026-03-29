import os
from typing import Optional

from simulators.base import Simulator
from simulators.cache_core import Cache, CacheConfig, CacheObj
from simulators.sim_utils import build_configspace, simulate_code, tune_code, update_code


class CacheSimulator(Simulator):
    def __init__(
        self,
        trace_path: str = None,
        trace_folder: str = None,
        capacity: int = None,
        consider_obj_size: bool = False,
        code_folder: str = None,
        key_col_id: int = 0,
        size_col_id: int = 1,
        has_header: bool = False,
        delimiter: str = ",",
        tune_runs: int = 20,
        tune_int_upper: int = None,
        timeout_seconds: int = 5,
    ):
        if trace_path is None and trace_folder is None:
            raise ValueError("Either trace_path or trace_folder must be provided")
        if trace_path is not None and trace_folder is not None:
            raise ValueError("Only one of trace_path or trace_folder can be provided")
        if capacity is None or capacity <= 0:
            raise ValueError("capacity must be set")
        if code_folder is None:
            raise ValueError("code_folder must be provided")
        super().__init__(name="Cache", code_folder=code_folder)
        self.capacity = capacity
        self.consider_obj_size = consider_obj_size
        self.key_col_id = key_col_id
        self.size_col_id = size_col_id
        self.has_header = has_header
        self.delimiter = delimiter
        if trace_folder is not None:
            if not os.path.exists(trace_folder):
                raise FileNotFoundError(trace_folder)
            trace_files = sorted(os.listdir(trace_folder))
            self.trace_paths = [os.path.join(trace_folder, t) for t in trace_files]
        else:
            self.trace_paths = [trace_path]
        self.tune_runs = tune_runs
        self.tune_int_upper = tune_int_upper
        self.timeout_seconds = timeout_seconds
        if self.tune_int_upper is None:
            self.tune_int_upper = capacity

    def _run(self, code: str):
        policy_module = {}
        exec(code, policy_module)
        scores = []
        for trace_path in self.trace_paths:
            config = CacheConfig(
                capacity=self.capacity,
                consider_obj_size=self.consider_obj_size,
                trace_path=trace_path,
                key_col_id=self.key_col_id,
                size_col_id=self.size_col_id,
                has_header=self.has_header,
                delimiter=self.delimiter,
            )
            cache = Cache(config, policy_module)
            with open(trace_path, "r") as f:
                if config.has_header:
                    next(f, None)
                for line in f:
                    if not line.strip():
                        continue
                    cols = line.strip().split(config.delimiter)
                    key = str(cols[config.key_col_id])
                    size = int(cols[config.size_col_id])
                    obj = CacheObj(key=key, size=size, consider_obj_size=config.consider_obj_size)
                    cache.get(obj)
            miss_ratio = cache.miss_count / cache.access_count if cache.access_count > 0 else 0.0
            scores.append(miss_ratio * 100)
        if not scores:
            return None
        return round(sum(scores) / len(scores), 4)

    def simulate(self, code: str, code_id: str) -> Optional[float]:
        return simulate_code(self, code, code_id, self._run, self.timeout_seconds)

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


def build_cache_simulator(
    capacity: int,
    consider_obj_size: bool,
    trace_folder: str = None,
    trace_path: str = None,
    code_folder: str = None,
    key_col_id: int = 0,
    size_col_id: int = 1,
    has_header: bool = False,
    delimiter: str = ",",
    tune_runs: int = 20,
    tune_int_upper: int = None,
    timeout_seconds: int = 5,
):
    if code_folder is None:
        code_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "log", "code")
        code_folder = os.path.abspath(code_folder)

    return CacheSimulator(
        trace_path=trace_path,
        trace_folder=trace_folder,
        capacity=capacity,
        consider_obj_size=consider_obj_size,
        code_folder=code_folder,
        key_col_id=key_col_id,
        size_col_id=size_col_id,
        has_header=has_header,
        delimiter=delimiter,
        tune_runs=tune_runs,
        tune_int_upper=tune_int_upper,
        timeout_seconds=timeout_seconds,
    )
