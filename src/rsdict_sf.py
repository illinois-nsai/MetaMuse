import logging

from .entry import Entry, EntryType
from .gpr import GPRConfig, GPRHintSelector
from .keyword_list import KeywordList
from .rsdict import RSDict


class RSDictSF(RSDict):
    def __init__(self, *args, gpr_config: GPRConfig = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.gpr_selector = GPRHintSelector(gpr_config)

    def _select_hints(self):
        hints_a = self.hint_sampler.sample(self.hint_word_count)
        hints_b = self.hint_sampler.sample(self.hint_word_count)
        idx = self.gpr_selector.choose_best(
            self.record_jsonl_path,
            [hints_a, hints_b],
            observation_fn=self._create_map_from_word,
        )
        return hints_a if idx == 0 else hints_b

    def _create_entry(self):
        logging.info("Creating Entry %s (RSDictSF)...", self.entry_counter)
        entry = Entry(id=self.entry_counter, entry_type=EntryType.RSDICT_SF)

        chosen_hints = self._select_hints()
        entry.hints = KeywordList(", ".join(chosen_hints))
        hint_description = self._create_map_from_keyword_list(entry.hints)
        design_prompt = self.problem.render_design_prompt(hint_description)
        design_dict = self.design_llm.answer(design_prompt)

        if design_dict is not None:
            entry.design = self._build_design(design_dict)
            code_prompt = self.problem.render_code_prompt(entry.design.to_dict())
            code_parser = self.code_llm.answer_parser
            if hasattr(code_parser, "set_code_id"):
                code_parser.set_code_id(self.entry_counter)
            evaluation_info_tuple = self.code_llm.answer(code_prompt)
            if evaluation_info_tuple is not None:
                entry.code = code_parser.simulator.code_path
                entry.evaluation_info = self._build_evaluation_info(evaluation_info_tuple)
                self._set_entry_fb_emb(entry)

        self.entry_counter += 1
        self.llm_call_counter += 1
        self._write_entry(entry)

    def _build_design(self, design_dict):
        from .design import Design

        return Design(design_dict)

    def _build_evaluation_info(self, evaluation_info_tuple):
        from .evaluation_info import EvaluationInfo

        return EvaluationInfo(
            default_score=evaluation_info_tuple[0],
            tuned_score=evaluation_info_tuple[1],
            default_params=evaluation_info_tuple[2],
            tuned_params=evaluation_info_tuple[3],
            metric_name=self.problem.metric_name,
        )

    def _write_entry(self, entry: Entry):
        from .utils import write_to_file

        write_to_file(
            dest_path=self.record_jsonl_path,
            contents=entry.to_jsonl() + "\n",
            is_append=True,
            is_json=False,
        )
