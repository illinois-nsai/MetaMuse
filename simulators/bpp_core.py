import pickle
from typing import List


class Bin:
    def __init__(self, id, cap, size):
        if not isinstance(id, int) or id < 0:
            raise ValueError(f"ID must be a non-negative integer: {id}")
        try:
            true_cap = int(cap)
        except Exception:
            true_cap = None
        if true_cap is None or true_cap < 0:
            raise ValueError(f"CAP must be non-negative integer: {true_cap}")
        try:
            true_size = int(size)
        except Exception:
            true_size = None
        if true_size is None or true_size < 0 or true_size > true_cap:
            raise ValueError(f"SIZE must be non-negative integer and not exceed CAP: {true_size} (cap={true_cap}).")
        self.__id = id
        self.__cap = true_cap
        self.__size = true_size

    @property
    def occupied_space(self):
        return self.__size

    @property
    def id(self):
        return self.__id

    @property
    def capacity(self):
        return self.__cap

    @property
    def remaining_space(self):
        r_space = self.__cap - self.__size
        if r_space < 0:
            raise ValueError("negative remaining space")
        return r_space


class BPPEvalConfig:
    def __init__(self, trace_path: str):
        if not trace_path:
            raise ValueError("trace_path is required")
        instances = pickle.load(open(trace_path, "rb"))
        self.trace_path = trace_path
        self.instance = None
        self.l1_bound = None
        if len(instances) != 2:
            raise ValueError("trace must contain instance and l1_bound")
        for name in instances:
            if name == "l1_bound":
                self.l1_bound = float(instances["l1_bound"])
            else:
                self.instance = instances[name]
        if self.instance is None or self.l1_bound is None:
            raise ValueError("invalid trace file")

    def to_dict(self):
        return {
            "trace_path": self.trace_path,
            "l1_bound": self.l1_bound,
        }


class BPPEval:
    def __init__(self, config: BPPEvalConfig, policy_module: dict):
        self.__item_list = config.instance["items"]
        self.__l1_bound = config.l1_bound
        if len(self.__item_list) != config.instance["num_items"]:
            raise ValueError("item list length mismatch")
        self.__bins: List[Bin] = []
        self.__bin_cap = config.instance["capacity"]
        if "select_bin" not in policy_module or "update_after_select" not in policy_module:
            raise ValueError("policy must define select_bin and update_after_select")
        self.select_bin_func = policy_module["select_bin"]
        self.update_after_select_func = policy_module["update_after_select"]

    @property
    def existing_bins_snapshot(self):
        return self.__bins

    def admit(self, item):
        if item == 0:
            return False
        if item > self.__bin_cap:
            return False
        return True

    def simulate(self):
        for item in self.__item_list:
            if not self.admit(item):
                continue

            if all(b.remaining_space < item for b in self.__bins):
                selected_bin_id = -1
            else:
                selected_bin_id = self.select_bin_func(self.existing_bins_snapshot, item)

            if selected_bin_id == -1:
                new_bin = Bin(id=len(self.__bins), cap=self.__bin_cap, size=item)
                self.__bins.append(new_bin)
            else:
                if not (0 <= selected_bin_id < len(self.__bins)):
                    raise ValueError("invalid bin id")
                selected_bin: Bin = self.__bins[selected_bin_id]
                if selected_bin.remaining_space < item:
                    raise ValueError("selected bin lacks space")
                new_bin = Bin(
                    id=selected_bin_id,
                    cap=self.__bin_cap,
                    size=item + selected_bin.occupied_space,
                )
                self.__bins[selected_bin_id] = new_bin

            self.update_after_select_func(self.existing_bins_snapshot, item, selected_bin_id)

        if any(b.occupied_space <= 0 for b in self.__bins):
            raise ValueError("empty bin")
        if sum(b.occupied_space for b in self.__bins) != sum(self.__item_list):
            raise ValueError("item total mismatch")
        if len(self.__bins) < self.__l1_bound:
            raise ValueError("bin count below lower bound")
        return (len(self.__bins) - self.__l1_bound) / self.__l1_bound
