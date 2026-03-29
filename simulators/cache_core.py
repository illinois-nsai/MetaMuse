from typing import Dict


class CacheObj:
    def __init__(self, key, size, consider_obj_size: bool):
        if not isinstance(key, str):
            raise ValueError("KEY must be a string.")
        if not isinstance(size, int) or size <= 0:
            raise ValueError("SIZE must be a positive integer.")
        self.__key = key
        self.__size = size if consider_obj_size else 1

    @property
    def size(self):
        return self.__size

    @property
    def key(self):
        return self.__key


class CacheConfig:
    def __init__(
        self,
        capacity: int,
        consider_obj_size: bool,
        trace_path: str,
        key_col_id: int,
        size_col_id: int,
        has_header: bool,
        delimiter: str,
    ):
        if not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("CAPACITY must be a positive integer.")
        if not isinstance(consider_obj_size, bool):
            raise ValueError("CONSIDER_OBJ_SIZE must be a boolean value.")
        self.capacity = capacity
        self.consider_obj_size = consider_obj_size
        self.trace_path = trace_path
        self.key_col_id = key_col_id
        self.size_col_id = size_col_id
        self.has_header = has_header
        self.delimiter = delimiter

    def to_dict(self) -> Dict:
        return {
            "capacity": self.capacity,
            "consider_obj_size": self.consider_obj_size,
            "trace_path": self.trace_path,
            "key_col_id": self.key_col_id,
            "size_col_id": self.size_col_id,
            "has_header": self.has_header,
            "delimiter": self.delimiter,
        }


class Cache:
    def __init__(self, config: CacheConfig, policy_module: dict):
        self.__capacity = config.capacity
        self.__cache = {}
        self.__naccess = 0
        self.__nhit = 0
        required = ["update_after_insert", "update_after_evict", "update_after_hit", "evict"]
        for key in required:
            if key not in policy_module:
                raise ValueError(f"policy must define {key}")
        self.update_after_insert_func = policy_module["update_after_insert"]
        self.update_after_evict_func = policy_module["update_after_evict"]
        self.update_after_hit_func = policy_module["update_after_hit"]
        self.evict_func = policy_module["evict"]

    @property
    def cache(self):
        return self.__cache

    @property
    def size(self):
        tot_size = 0
        for obj in self.__cache.values():
            tot_size += obj.size
        return tot_size

    @property
    def capacity(self):
        return self.__capacity

    @property
    def access_count(self):
        return self.__naccess

    @property
    def hit_count(self):
        return self.__nhit

    @property
    def miss_count(self):
        return self.__naccess - self.__nhit

    @property
    def snapshot(self):
        return self

    def get(self, obj: CacheObj) -> bool:
        self.__naccess += 1
        if obj.key in self.cache:
            self.__nhit += 1
            self.update_after_hit(obj)
            return True

        if not self.can_insert(obj):
            return False
        if not self.admit(obj):
            return False
        while self.size + obj.size > self.capacity:
            evicted_cache_object = self.evict(obj)
            self.update_after_evict(obj, evicted_cache_object)
        self.insert(obj)
        self.update_after_insert(obj)
        return False

    def update_after_hit(self, obj):
        self.update_after_hit_func(self.snapshot, obj)

    def update_after_insert(self, obj):
        self.update_after_insert_func(self.snapshot, obj)

    def update_after_evict(self, obj, evicted_obj):
        self.update_after_evict_func(self.snapshot, obj, evicted_obj)

    def evict(self, obj):
        candid_obj_key = self.evict_func(self.snapshot, obj)
        if candid_obj_key is None or candid_obj_key not in self.__cache:
            raise ValueError("evict must return an existing cache key")
        return self.__cache.pop(candid_obj_key)

    def insert(self, obj):
        self.__cache[obj.key] = obj

    def can_insert(self, obj):
        return obj.size <= self.capacity

    def admit(self, obj):
        return self.capacity >= obj.size
