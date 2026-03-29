import logging
import os
import random
from typing import Optional

from . import logging_config

from .design import Design
from .entry import Entry, EntryType
from .feedback_embedding import FeedbackEmbedding
from .hint_sampler import HintSampler
from .keyword_list import KeywordList
from .llm import LLM, LLMConfig, LLMSupplierType
from .evaluation_info import EvaluationInfo
from .parser import CodeParser, DesignJsonParser, MapParser
from .problem import ProblemSpec
from .simulator_api import SimulatorLike
from .utils import write_to_file


class RSDict:
    def __init__(
        self,
        problem: ProblemSpec,
        simulator: SimulatorLike,
        feedback_embedding: FeedbackEmbedding,
        llm_supplier: LLMSupplierType,
        tot_llm_call_num: int,
        hint_word_count: int,
        wordlist_path: Optional[str] = None,
        log_dir: Optional[str] = None,
        seed: int = 42,
    ):
        random.seed(seed)
        if tot_llm_call_num < 0:
            raise ValueError("tot_llm_call_num must be non-negative")
        if hint_word_count <= 0:
            raise ValueError("hint_word_count must be positive")

        self.tot_llm_call_num = tot_llm_call_num
        self.hint_word_count = hint_word_count
        self.entry_counter = 0
        self.llm_call_counter = 0
        self.keyword_map = {}
        self.feedback_embedding = feedback_embedding

        if problem is None:
            raise ValueError("problem must be provided")
        self.problem = problem
        self.simulator = simulator
        if wordlist_path is None:
            wordlist_path = os.path.join(os.path.dirname(__file__), "data", "en_3000.txt")
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")

        self.record_jsonl_path = os.path.join(log_dir, "record.jsonl")
        self.statistics_json_path = os.path.join(log_dir, "statistics.json")

        self.hint_sampler = HintSampler(wordlist_path=wordlist_path, seed=seed)

        self.map_llm = LLM(
            LLMConfig(
                llm_name="Map",
                trial_num=3,
                temperature=1.0,
                answer_parser=MapParser(),
                llm_supplier=llm_supplier,
            )
        )
        self.design_llm = LLM(
            LLMConfig(
                llm_name="Design",
                trial_num=3,
                temperature=1.0,
                answer_parser=DesignJsonParser(required_keys=self.problem.design_required_keys),
                llm_supplier=llm_supplier,
            )
        )
        self.code_llm = LLM(
            LLMConfig(
                llm_name="Code",
                trial_num=3,
                temperature=0.5,
                answer_parser=CodeParser(unique_simulator=simulator),
                llm_supplier=llm_supplier,
            )
        )

    def _set_entry_fb_emb(self, entry: Entry):
        if entry.code is None:
            raise ValueError("entry.code is missing")
        if self.problem.code_extension and not entry.code.endswith(self.problem.code_extension):
            raise ValueError(f"entry.code must be a {self.problem.code_extension} file")
        if not os.path.exists(entry.code):
            raise FileNotFoundError(entry.code)
        with open(entry.code, "r") as file:
            code = file.read()
        entry.fb_emb = self.feedback_embedding.embed(code)
        return entry.fb_emb

    def _create_map_from_word(self, word: str):
        word_key = word.strip().lower()
        if word_key in self.keyword_map:
            return self.keyword_map[word_key]
        map_prompt = self.problem.render_map_prompt(word_key)
        descrip = self.map_llm.answer(map_prompt)
        self.keyword_map[word_key] = descrip
        return descrip

    def _create_map_from_keyword_list(self, keywords_list: KeywordList):
        descrip_list = []
        for keyword in keywords_list.keyword_list:
            descrip = self._create_map_from_word(keyword)
            if descrip is not None:
                descrip_list.append(descrip)
        if not descrip_list:
            return "No hints."
        return "\n".join([f"- {d}" for d in descrip_list])

    def _create_entry(self):
        logging.info("Creating Entry %s...", self.entry_counter)
        entry = Entry(id=self.entry_counter, entry_type=EntryType.RSDICT)

        hints = self.hint_sampler.sample(self.hint_word_count)
        entry.hints = KeywordList(", ".join(hints))
        hint_description = self._create_map_from_keyword_list(entry.hints)
        design_prompt = self.problem.render_design_prompt(hint_description)
        design_dict = self.design_llm.answer(design_prompt)

        if design_dict is not None:
            entry.design = Design(design_dict)
            code_prompt = self.problem.render_code_prompt(entry.design.to_dict())
            code_parser = self.code_llm.answer_parser
            if isinstance(code_parser, CodeParser):
                code_parser.set_code_id(self.entry_counter)
            evaluation_info_tuple = self.code_llm.answer(code_prompt)
            if evaluation_info_tuple is not None:
                entry.code = code_parser.simulator.code_path
                entry.evaluation_info = EvaluationInfo(
                    default_score=evaluation_info_tuple[0],
                    tuned_score=evaluation_info_tuple[1],
                    default_params=evaluation_info_tuple[2],
                    tuned_params=evaluation_info_tuple[3],
                    metric_name=self.problem.metric_name,
                )
                self._set_entry_fb_emb(entry)

        self.entry_counter += 1
        self.llm_call_counter += 1
        write_to_file(
            dest_path=self.record_jsonl_path,
            contents=entry.to_jsonl() + "\n",
            is_append=True,
            is_json=False,
        )

    def init(self):
        pass

    def optimize(self):
        self.init()
        while self.llm_call_counter < self.tot_llm_call_num:
            self._create_entry()
        write_to_file(
            dest_path=self.statistics_json_path,
            contents=self.to_dict(),
            is_append=False,
            is_json=True,
        )

    def to_dict(self) -> dict:
        return {
            "tot_llm_call_num": self.tot_llm_call_num,
            "hint_word_count": self.hint_word_count,
            "keyword_map": self.keyword_map,
            "map_llm": self.map_llm.to_dict(),
            "design_llm": self.design_llm.to_dict(),
            "code_llm": self.code_llm.to_dict(),
            "feedback_embedding": self.feedback_embedding.to_dict(),
            "problem": self.problem.to_dict(),
            "simulator": self.simulator.to_dict(),
            "entry_counter": self.entry_counter,
            "llm_call_counter": self.llm_call_counter,
            "record_jsonl_path": self.record_jsonl_path,
            "statistics_json_path": self.statistics_json_path,
            "wordlist_path": self.hint_sampler.wordlist_path,
        }
