"""Sandboxed script runner for Code Wars (phase 1).

Runs a player script with a restricted builtins table and an instruction
budget enforced through sys.settrace. This is a first layer only; the process
boundary and memory limits are still to be added (see ARCHITECTURE.md).
"""
import builtins
import io
import sys
import traceback

MAX_LINES = 200_000

_SAFE = [
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len",
    "list", "max", "min", "print", "range", "round", "sorted", "str", "sum",
    "tuple", "zip", "True", "False", "None", "isinstance", "reversed",
    "ValueError", "TypeError", "Exception", "ZeroDivisionError", "IndexError",
    "KeyError",
]


class BudgetExceeded(Exception):
    pass


def run_script(source, entry="update", arg_dict=None):
    out = io.StringIO()
    safe = {n: getattr(builtins, n) for n in _SAFE}
    safe["print"] = lambda *a, **k: print(*a, file=out, **k)
    env = {"__builtins__": safe}
    count = [0]

    def tracer(frame, event, a):
        if event == "line":
            count[0] += 1
            if count[0] > MAX_LINES:
                raise BudgetExceeded("instruction budget exceeded")
        return tracer

    try:
        code = compile(source, "<player>", "exec")
        sys.settrace(tracer)
        try:
            exec(code, env)
            fn = env.get(entry)
            result = fn(arg_dict) if callable(fn) else None
        finally:
            sys.settrace(None)
        return {"ok": True, "output": out.getvalue(), "result": repr(result),
                "steps": count[0]}
    except BudgetExceeded as e:
        return {"ok": False, "output": out.getvalue(), "error": str(e),
                "steps": count[0]}
    except BaseException:
        return {"ok": False, "output": out.getvalue(),
                "error": traceback.format_exc(limit=3), "steps": count[0]}
