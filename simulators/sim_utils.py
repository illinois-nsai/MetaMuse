import logging
import os
import re
import signal
import time
import traceback
from datetime import datetime

from openbox import Optimizer
from openbox import space as sp

from src.utils import write_to_file


class TimeoutException(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutException("Function execution timed out")


def timeout(seconds):
    def decorator(func):
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(seconds)
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)
        return wrapper
    return decorator


def run_with_timeout(run_fn, timeout_seconds, *args, **kwargs):
    if timeout_seconds <= 0:
        return run_fn(*args, **kwargs)
    return timeout(timeout_seconds)(run_fn)(*args, **kwargs)


def extract_string(text: str, regex: str, group_id: int):
    match = re.search(regex, text, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(group_id)
    return None


def is_expr(text: str) -> bool:
    return "=" in text and all(c + "=" not in text for c in ["!", "=", "*", "+", "-", "/", "|", "%", "^"])


def get_type_and_value(text: str):
    if text.strip().lower() == "true":
        return bool, True
    if text.strip().lower() == "false":
        return bool, False
    try:
        float(text)
        if "0." in text:
            return float, float(text)
        if "." in text:
            return int, int(float(text))
        raise ValueError
    except ValueError:
        try:
            int(text)
            return int, int(text)
        except ValueError:
            return None


def modify_string(text: str, regex: str, group_id: int, modification: str) -> str:
    match = re.search(regex, text, re.DOTALL | re.MULTILINE)
    if match:
        return text[:match.start(group_id)] + str(modification) + text[match.end(group_id):]
    return text


def build_configspace(code: str, fixed_default: bool, tune_int_upper: int):
    space = sp.Space()
    tp_pattern = r"(# Put tunable constant parameters below\\s*\\n)(.*?)(?=^# Put the metadata specifically maintained by the policy below)"
    tunable_parameters = extract_string(text=code, regex=tp_pattern, group_id=2)
    if tunable_parameters is None or tunable_parameters.strip() == "":
        return None
    candid_exprs = tunable_parameters.split("\n")
    optimizer_params = []
    for cexpr in candid_exprs:
        if not is_expr(cexpr):
            continue
        rhs_pattern = r"=\\s*(.*?)\\s*(#.*)?$"
        rhs = extract_string(text=cexpr, regex=rhs_pattern, group_id=1)
        if rhs is None:
            continue
        type_and_value = get_type_and_value(rhs)
        if type_and_value is None:
            continue
        var_name = str(len(optimizer_params))
        var_type, value = type_and_value
        if var_type == bool:
            var_default = 1 if value else 0
            if fixed_default:
                var_default = 1
            optimizer_params.append(sp.Int(var_name, 0, 1, default_value=var_default))
        elif var_type == int:
            var_default = int(value)
            if fixed_default:
                var_default = 3
            var_lower = min(var_default, 1)
            var_upper = max(tune_int_upper, 2 * var_default, var_lower)
            optimizer_params.append(sp.Int(var_name, var_lower, var_upper, default_value=var_default))
        else:
            var_default = float(value)
            if fixed_default:
                var_default = 0.42
            var_lower = min(var_default, 0.0)
            var_upper = max(var_default, 1.0)
            optimizer_params.append(sp.Real(var_name, var_lower, var_upper, default_value=var_default))

    if not optimizer_params:
        return None
    space.add_variables(optimizer_params)
    return space


def update_code(code: str, params: dict):
    tp_pattern = r"(# Put tunable constant parameters below\\s*\\n)(.*?)(?=^# Put the metadata specifically maintained by the policy below)"
    tunable_parameters = extract_string(text=code, regex=tp_pattern, group_id=2)
    candid_exprs = tunable_parameters.split("\n")
    new_cexprs = []
    param_id = 0
    for cexpr in candid_exprs:
        new_cexprs.append(cexpr)
        if not is_expr(cexpr):
            continue
        rhs_pattern = r"=\\s*(.*?)\\s*(#.*)?$"
        rhs = extract_string(text=cexpr, regex=rhs_pattern, group_id=1)
        if rhs is None:
            continue
        if get_type_and_value(rhs) is None:
            continue
        new_cexpr = modify_string(text=cexpr, regex=rhs_pattern, group_id=1, modification=str(params[str(param_id)]))
        new_cexprs[-1] = new_cexpr
        param_id += 1

    new_tunable_parameters = "\n".join(new_cexprs)
    return modify_string(text=code, regex=tp_pattern, group_id=2, modification=new_tunable_parameters)


def write_error_log(code_path: str, error_code_id: str, error_msg: str, traceback_msg: str = ""):
    error_code_path = code_path.replace(".py", ".error")
    error_log = (
        f"**************************************************{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**************************************************\n"
        + f"[code_id]: {error_code_id}\n[error_msg]: {error_msg}\n[traceback_msg]:\n{traceback_msg}"
        + "\n=======================================================================================================================\n\n"
    )
    write_to_file(dest_path=error_code_path, contents=error_log, is_append=True, is_json=False)


def simulate_code(sim, code: str, code_id: str, run_fn, timeout_seconds: int, on_error=None):
    sim.code_path = os.path.join(sim.code_folder, f"{code_id}.py")
    start = time.time()
    try:
        result = run_with_timeout(run_fn, timeout_seconds, code)
    except Exception as error:
        sim.latency += time.time() - start
        logging.warning("New code: %s\n\tFAIL...\n\tError message: %s", code_id, repr(error))
        write_error_log(sim.code_path, code_id, "(Simulation) " + repr(error), traceback.format_exc().strip())
        if on_error is not None:
            on_error()
        return None
    sim.latency += time.time() - start
    write_to_file(dest_path=sim.code_path, contents=code.strip(), is_append=False, is_json=False)
    return result


def tune_code(
    sim,
    code: str,
    code_id: str,
    fixed_default_param: bool,
    get_configspace_fn,
    update_code_fn,
    run_fn,
    timeout_seconds: int,
    tune_runs: int,
):
    sim.code_path = os.path.join(sim.code_folder, f"{code_id}.py")
    config_space = get_configspace_fn(code, fixed_default_param)
    if config_space is None:
        return None
    default_params = {k: v.default_value for k, v in dict(config_space).items()}

    def objective(config_space):
        params = dict(config_space).copy()
        new_code = update_code_fn(code, params)
        try:
            score = run_with_timeout(run_fn, timeout_seconds, new_code)
        except Exception:
            score = 1.0
        return dict(objectives=[score])

    opt = Optimizer(
        objective_function=objective,
        config_space=config_space,
        num_objectives=1,
        num_constraints=0,
        max_runs=tune_runs,
        surrogate_type="prf",
        visualization="none",
    )

    opt_score = None
    tuned_params = None
    error_log = None
    start = time.time()
    try:
        history = opt.run()
    except Exception as error:
        error_log = True
        logging.info("Tuning code %s: FAIL...\n\tError message: %s", code_id, repr(error))
        write_error_log(sim.code_path, code_id, "(Tuning) " + repr(error), traceback.format_exc().strip())
    sim.latency += time.time() - start

    if error_log is None and len(history.get_incumbents()) > 0:
        opt_score = history.get_incumbent_value()
        tuned_params = dict(history.get_incumbent_configs()[0]).copy()

    return opt_score, default_params, tuned_params
