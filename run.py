import argparse
import os

from simulators.bpp_online import BPPOnlineSimulator
from simulators.cache import CacheSimulator
from src.feedback_embedding import FeedbackEmbedding
from src.llm import LLMSupplierType
from src.problem import ProblemSpec
from src.rsdict import RSDict
from src.rsdict_sf import RSDictSF
from src.gpr import GPRConfig


def _llm_supplier_from_str(name: str) -> LLMSupplierType:
    name = name.lower()
    if name == "openai":
        return LLMSupplierType.OPENAI
    if name == "llama33":
        return LLMSupplierType.LLAMA33
    if name == "deepseekv3":
        return LLMSupplierType.DEEPSEEKV3
    raise ValueError(f"Unknown llm supplier: {name}")


def build_problem_spec(problem: str, repo_root: str) -> ProblemSpec:
    if problem == "bpp_online":
        prompt_dir = os.path.join(repo_root, "prompts", "bpp_online")
        return ProblemSpec.from_dir(
            name="bpp_online",
            prompt_dir=prompt_dir,
            design_required_keys=["metadata", "select_bin", "update_after_select"],
            metric_name="miss_ratio",
        )
    if problem == "cache":
        prompt_dir = os.path.join(repo_root, "prompts", "cache")
        return ProblemSpec.from_dir(
            name="cache",
            prompt_dir=prompt_dir,
            design_required_keys=["metadata", "evict", "update_after_hit", "update_after_insert", "update_after_evict"],
            metric_name="miss_ratio",
        )
    raise ValueError(f"Unknown problem: {problem}")


def build_simulator(args):
    if args.problem == "bpp_online":
        return BPPOnlineSimulator(
            trace_folder=args.trace_folder,
            code_folder=args.code_folder,
            tune_runs=args.tune_runs,
            tune_int_upper=args.tune_int_upper,
            timeout_seconds=args.timeout_seconds,
        )
    if args.problem == "cache":
        return CacheSimulator(
            trace_folder=args.trace_folder,
            capacity=args.capacity,
            consider_obj_size=args.consider_obj_size,
            code_folder=args.code_folder,
            key_col_id=args.key_col_id,
            size_col_id=args.size_col_id,
            has_header=args.has_header,
            delimiter=args.delimiter,
            tune_runs=args.tune_runs,
            tune_int_upper=args.tune_int_upper,
            timeout_seconds=args.timeout_seconds,
        )
    raise ValueError(f"Unknown problem: {args.problem}")


def build_rsdict(args, problem, simulator):
    feedback_embedding = FeedbackEmbedding([simulator])
    llm_supplier = _llm_supplier_from_str(args.llm_supplier)

    if args.algo == "rsdict":
        return RSDict(
            problem=problem,
            simulator=simulator,
            feedback_embedding=feedback_embedding,
            llm_supplier=llm_supplier,
            tot_llm_call_num=args.tot_llm_call_num,
            hint_word_count=args.hint_word_count,
            wordlist_path=args.wordlist_path,
            log_dir=args.log_dir,
            seed=args.seed,
        )
    if args.algo == "rsdict_sf":
        gpr_config = GPRConfig(
            warmup=args.gpr_warmup,
            window_size=args.gpr_window_size,
            reduce_feature_dim=args.gpr_reduce_dim,
            kernel=args.gpr_kernel,
        )
        return RSDictSF(
            problem=problem,
            simulator=simulator,
            feedback_embedding=feedback_embedding,
            llm_supplier=llm_supplier,
            tot_llm_call_num=args.tot_llm_call_num,
            hint_word_count=args.hint_word_count,
            wordlist_path=args.wordlist_path,
            log_dir=args.log_dir,
            seed=args.seed,
            gpr_config=gpr_config,
        )
    raise ValueError(f"Unknown algorithm: {args.algo}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run RSDict or RSDict-SF on BPP or Cache")
    parser.add_argument("--algo", choices=["rsdict", "rsdict_sf"], required=True)
    parser.add_argument("--problem", choices=["bpp_online", "cache"], required=True)

    parser.add_argument("--trace_folder", required=True)
    parser.add_argument("--code_folder", required=True)

    parser.add_argument("--tot_llm_call_num", type=int, required=True)
    parser.add_argument("--hint_word_count", type=int, required=True)
    parser.add_argument("--wordlist_path", default=None)
    parser.add_argument("--log_dir", default=None)
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument("--llm_supplier", default="openai", choices=["openai", "llama33", "deepseekv3"])

    parser.add_argument("--tune_runs", type=int, default=20)
    parser.add_argument("--tune_int_upper", type=int, default=None)
    parser.add_argument("--timeout_seconds", type=int, default=5)

    parser.add_argument("--capacity", type=int, default=0)
    parser.add_argument("--consider_obj_size", action="store_true")
    parser.add_argument("--key_col_id", type=int, default=0)
    parser.add_argument("--size_col_id", type=int, default=1)
    parser.add_argument("--has_header", action="store_true")
    parser.add_argument("--delimiter", default=",")

    parser.add_argument("--gpr_warmup", type=int, default=100)
    parser.add_argument("--gpr_window_size", type=int, default=2)
    parser.add_argument("--gpr_reduce_dim", type=int, default=None)
    parser.add_argument("--gpr_kernel", default="dotproduct", choices=["dotproduct", "matern_nu2.5", "matern_nu1.5", "rbf"])

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.problem == "cache" and args.capacity <= 0:
        raise ValueError("--capacity must be set for cache")

    repo_root = os.path.dirname(os.path.abspath(__file__))
    problem = build_problem_spec(args.problem, repo_root)
    simulator = build_simulator(args)
    rsdict = build_rsdict(args, problem, simulator)
    rsdict.optimize()


if __name__ == "__main__":
    main()
