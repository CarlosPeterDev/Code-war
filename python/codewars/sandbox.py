"""Sandboxed execution of player Python.

Layers: (1) AST validation (no imports except whitelisted modules, no dunder/underscore
attribute access, no str.format, no exec/eval/open/getattr...), (2) restricted builtins,
(3) arithmetic guards for pow/mult/range to stop C-level memory/time bombs,
(4) per-run line (instruction) budget and wall-clock deadline via sys.settrace,
(5) coarse memory budget via tracemalloc sampling.

Limits: this is an in-process sandbox, not an OS process boundary. A single very long C call
that the guards do not cover could still stall a run; see ARCHITECTURE.md.
"""
import ast
import builtins as _b
import math
import random as _random
import sys
import time
import traceback
import tracemalloc

FORBIDDEN_NAMES = {
    "exec", "eval", "compile", "open", "input", "__import__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "breakpoint", "memoryview", "help", "exit", "quit",
    "dir", "type", "super", "object", "classmethod", "staticmethod", "property",
}
FORBIDDEN_ATTRS = {"format", "format_map", "mro", "with_traceback", "throw", "send", "close"}
# frame/code/traceback/generator introspection attributes (not dunders, but they reach interpreter internals)
FORBIDDEN_ATTR_PREFIXES = ("gi_", "cr_", "ag_", "f_", "tb_", "co_", "func_", "im_")
ALLOWED_MODULES = {"math", "random"}
MAX_SEQ = 50000
MAX_RANGE = 100000
MAX_POW_EXP = 64
MAX_INT_BITS = 4096

SAFE_BUILTIN_NAMES = [
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "int", "isinstance",
    "len", "list", "map", "max", "min", "pow", "print", "reversed", "round", "set", "sorted",
    "str", "sum", "tuple", "zip", "chr", "ord", "bin", "hex", "repr", "frozenset", "bytes",
    "True", "False", "None", "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "ZeroDivisionError", "AttributeError", "RuntimeError", "StopIteration", "ArithmeticError",
    "NotImplemented", "callable", "hash", "id", "iter", "next", "slice",
]


class BudgetExceeded(Exception):
    """Raised inside player code when a budget (lines/time/memory) is exhausted."""


class SandboxError(Exception):
    pass


def validate_source(source, filename="<script>"):
    """Static checks. Returns list of dicts {line, col, message, severity}."""
    problems = []
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        return [dict(line=e.lineno or 1, col=(e.offset or 1), severity="error",
                     message="Syntax error: %s" % (e.msg,))]

    def bad(node, msg):
        problems.append(dict(line=getattr(node, "lineno", 1), col=getattr(node, "col_offset", 0) + 1,
                             severity="error", message=msg))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_MODULES:
                    bad(node, "Import of '%s' is not allowed. Allowed modules: %s." % (
                        a.name, ", ".join(sorted(ALLOWED_MODULES))))
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_MODULES or node.level:
                bad(node, "Import from '%s' is not allowed. Allowed modules: %s." % (
                    node.module, ", ".join(sorted(ALLOWED_MODULES))))
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                bad(node, "Access to attributes starting with '_' is not allowed ('%s')." % node.attr)
            elif node.attr in FORBIDDEN_ATTRS or node.attr.startswith(FORBIDDEN_ATTR_PREFIXES):
                bad(node, ("'.%s()' is not allowed in the sandbox (use f-strings instead)." % node.attr)
                    if node.attr.startswith("format") else
                    "'.%s' is not allowed in the sandbox." % node.attr)
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                bad(node, "Use of '%s' is not allowed in the sandbox." % node.id)
            elif node.id.startswith("__") and node.id not in ("__name__",):
                bad(node, "Names starting with '__' are not allowed.")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)):
            bad(node, "async code is not supported.")
        elif isinstance(node, ast.ClassDef):
            bad(node, "Class definitions are not supported; use functions, lists and dicts.")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bad(node, "global/nonlocal are not supported; keep state in robot.memory.")
    return problems


def _safe_pow(a, b, mod=None):
    if isinstance(a, int) and isinstance(b, int) and not isinstance(a, bool):
        if b > MAX_POW_EXP and abs(a) > 1:
            raise BudgetExceeded("exponent %d too large (max %d)" % (b, MAX_POW_EXP))
        if b >= 0 and abs(a) > 1 and abs(a).bit_length() * b > MAX_INT_BITS:
            raise BudgetExceeded("result of ** would be too large")
    return pow(a, b) if mod is None else pow(a, b, mod)


def _safe_mul(a, b):
    for seq, n in ((a, b), (b, a)):
        if isinstance(seq, (str, bytes, list, tuple)) and isinstance(n, int):
            if len(seq) * max(n, 0) > MAX_SEQ:
                raise BudgetExceeded("sequence repeat too large (max %d items)" % MAX_SEQ)
    if isinstance(a, int) and isinstance(b, int) and a.bit_length() + b.bit_length() > MAX_INT_BITS:
        raise BudgetExceeded("integer too large")
    return a * b


def _seq_len(v):
    return len(v) if isinstance(v, (str, bytes, list, tuple, set, dict, frozenset)) else None


def _safe_add(a, b):
    la, lb = _seq_len(a), _seq_len(b)
    if la is not None and lb is not None and la + lb > MAX_SEQ:
        raise BudgetExceeded("sequence too large (max %d items)" % MAX_SEQ)
    return a + b


def _safe_iadd(a, b):
    la, lb = _seq_len(a), _seq_len(b)
    if la is not None and lb is not None and la + lb > MAX_SEQ:
        raise BudgetExceeded("sequence too large (max %d items)" % MAX_SEQ)
    a += b            # keeps real Python aliasing semantics for lists
    return a


def _safe_imul(a, b):
    if isinstance(a, (str, bytes, list, tuple)) and isinstance(b, int) and len(a) * max(b, 0) > MAX_SEQ:
        raise BudgetExceeded("sequence repeat too large (max %d items)" % MAX_SEQ)
    if isinstance(a, int) and isinstance(b, int) and a.bit_length() + b.bit_length() > MAX_INT_BITS:
        raise BudgetExceeded("integer too large")
    a *= b
    return a


def _safe_shift(a, b):
    if isinstance(a, int) and isinstance(b, int) and b > 0 and a.bit_length() + b > MAX_INT_BITS:
        raise BudgetExceeded("shift result too large")
    return a << b


_GUARDED_METHODS = {"join", "ljust", "rjust", "center", "zfill", "replace", "extend", "expandtabs"}


def _safe_method(obj, name, *args, **kw):
    """Pre-checks the result size of methods that can amplify memory in one call."""
    big = BudgetExceeded("result too large (max %d items)" % MAX_SEQ)
    if isinstance(obj, str):
        if name in ("ljust", "rjust", "center", "zfill") and args and isinstance(args[0], int) and args[0] > MAX_SEQ:
            raise big
        if name == "expandtabs" and (len(obj) * (args[0] if args and isinstance(args[0], int) else 8) > MAX_SEQ):
            raise big
        if name == "replace" and len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], str):
            n = obj.count(args[0]) if args[0] else len(obj) + 1
            if len(obj) + n * len(args[1]) > MAX_SEQ:
                raise big
        if name == "join" and args:
            items = list(args[0])
            if sum(len(i) for i in items if isinstance(i, str)) + len(obj) * len(items) > MAX_SEQ:
                raise big
            args = (items,)
    elif isinstance(obj, list) and name == "extend" and args:
        it = args[0] if isinstance(args[0], (list, tuple, set, frozenset, str, dict)) else list(args[0])
        if len(obj) + len(it) > MAX_SEQ:
            raise big
        args = (it,)
    fn = getattr(obj, name)
    return fn(*args, **kw)


class _Rewriter(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in _GUARDED_METHODS and not node.keywords or \
                (isinstance(f, ast.Attribute) and f.attr in _GUARDED_METHODS and node.keywords and
                 not any(k.arg is None for k in node.keywords)):
            args = [f.value, ast.Constant(f.attr)] + list(node.args)
            return ast.copy_location(ast.Call(ast.Name("_cw_m", ast.Load()), args, node.keywords), node)
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        names = {ast.Pow: "_cw_pow", ast.Mult: "_cw_mul", ast.Add: "_cw_add", ast.LShift: "_cw_shl"}
        fn = names.get(type(node.op))
        if fn:
            return ast.copy_location(ast.Call(ast.Name(fn, ast.Load()), [node.left, node.right], []), node)
        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        names = {ast.Pow: "_cw_pow", ast.Mult: "_cw_imul", ast.Add: "_cw_iadd", ast.LShift: "_cw_shl"}
        fn = names.get(type(node.op))
        if fn:
            load = ast.copy_location(_to_load(node.target), node)
            call = ast.copy_location(ast.Call(ast.Name(fn, ast.Load()), [load, node.value], []), node)
            return ast.copy_location(ast.Assign([node.target], call), node)
        return node


def _to_load(target):
    import copy
    t = copy.deepcopy(target)
    for n in ast.walk(t):
        if hasattr(n, "ctx"):
            n.ctx = ast.Load()
    return t


def _safe_range(*args):
    r = range(*args)
    if len(r) > MAX_RANGE:
        raise BudgetExceeded("range too long (max %d)" % MAX_RANGE)
    return r


def _make_import(rng):
    class _RandomProxy:
        def random(self):
            return rng.random()

        def randint(self, a, b):
            return rng.randint(a, b)

        def choice(self, seq):
            return rng.choice(seq)

        def uniform(self, a, b):
            return rng.uniform(a, b)

        def shuffle(self, seq):
            rng.shuffle(seq)

    proxy = _RandomProxy()

    def _imp(name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".")[0]
        if root == "math":
            return _SAFE_MATH
        if root == "random":
            return proxy
        raise ImportError("import of '%s' is not allowed" % name)
    return _imp


_mem_started = False


def _ensure_tracemalloc():
    global _mem_started
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    _mem_started = True


class CompiledScript:
    def __init__(self, name, source):
        self.name = name
        self.source = source
        self.problems = validate_source(source, name)
        self.code = None
        if not any(p["severity"] == "error" for p in self.problems):
            tree = ast.parse(source, filename="<player:%s>" % name)
            tree = ast.fix_missing_locations(_Rewriter().visit(tree))
            self.code = compile(tree, "<player:%s>" % name, "exec")
        self.filename = "<player:%s>" % name


_MATH_OK = ["sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "hypot", "floor", "ceil", "pi", "e",
            "fabs", "log", "log2", "log10", "exp", "degrees", "radians", "dist", "inf", "isclose", "copysign",
            "fmod", "trunc", "gcd", "isqrt", "tau", "sinh", "cosh", "tanh"]


class _SafeMath:
    pass


def _make_math():
    m = _SafeMath()
    for n in _MATH_OK:
        setattr(m, n, getattr(math, n))
    return m


_SAFE_MATH = _make_math()


def make_namespace(log_fn, rng):
    safe = {n: getattr(_b, n) for n in SAFE_BUILTIN_NAMES if hasattr(_b, n)}
    safe["print"] = lambda *a, **k: log_fn(" ".join(str(x) for x in a))
    safe["range"] = _safe_range
    safe["pow"] = _safe_pow
    safe["__import__"] = _make_import(rng)
    ns = {"__builtins__": safe, "__name__": "player", "_cw_pow": _safe_pow, "_cw_mul": _safe_mul,
          "_cw_add": _safe_add, "_cw_iadd": _safe_iadd, "_cw_imul": _safe_imul, "_cw_shl": _safe_shift,
          "_cw_m": _safe_method, "math": _SAFE_MATH}
    return ns


class Budget:
    """Line/time/memory budget enforced by a trace function."""

    def __init__(self, max_lines, max_seconds, max_mem_bytes=16 * 1024 * 1024, check_memory=True):
        self.max_lines = max_lines
        self.max_seconds = max_seconds
        self.max_mem = max_mem_bytes
        self.check_memory = check_memory
        self.lines = 0
        self.deadline = None
        self.mem_base = 0
        self.breakpoints = None   # {filename: set(lines)}
        self.snapshots = []
        self.line_trace = None    # optional list for execution trace

    def tracer(self, filename):
        def local(frame, event, arg):
            if event == "line":
                self.lines += 1
                if self.lines > self.max_lines:
                    raise BudgetExceeded("instruction budget exceeded (%d lines)" % self.max_lines)
                if (self.lines & 15) == 0:
                    if time.perf_counter() > self.deadline:
                        raise BudgetExceeded("time budget exceeded (%.0f ms)" % (self.max_seconds * 1000))
                    if self.check_memory and tracemalloc.is_tracing():
                        cur = tracemalloc.get_traced_memory()[0]
                        if cur - self.mem_base > self.max_mem:
                            raise BudgetExceeded("memory budget exceeded")
                if self.breakpoints and frame.f_lineno in self.breakpoints.get(filename, ()):
                    if len(self.snapshots) < 60:
                        self.snapshots.append(dict(line=frame.f_lineno, function=frame.f_code.co_name,
                                                   variables=_snapshot_vars(frame.f_locals)))
                if self.line_trace is not None and len(self.line_trace) < 400:
                    self.line_trace.append(frame.f_lineno)
            return local

        def global_t(frame, event, arg):
            if event == "call" and frame.f_code.co_filename == filename:
                return local
            return None
        return global_t


def _snapshot_vars(d):
    out = {}
    for k, v in list(d.items())[:40]:
        if k.startswith("_") or k in ("robot", "base") and False:
            continue
        try:
            if callable(v) and not isinstance(v, type):
                continue
            r = repr(v)
        except Exception:
            r = "<unrepresentable>"
        out[k] = r[:120]
    return out


def run_call(script_filename, fn, args, budget):
    """Run fn(*args) under budget. Returns (ok, result_or_error_string)."""
    budget.deadline = time.perf_counter() + budget.max_seconds
    if budget.check_memory:
        _ensure_tracemalloc()
        budget.mem_base = tracemalloc.get_traced_memory()[0]
    old = sys.gettrace()
    sys.settrace(budget.tracer(script_filename))
    try:
        return True, fn(*args)
    except BudgetExceeded as e:
        return False, "BudgetExceeded: %s" % e
    except RecursionError:
        return False, "RecursionError: recursion too deep"
    except Exception as e:
        return False, _format_error(e, script_filename)
    finally:
        sys.settrace(old)


def _format_error(e, filename):
    tb = e.__traceback__
    line = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == filename:
            line = tb.tb_lineno
        tb = tb.tb_next
    where = " (line %d)" % line if line else ""
    return "%s: %s%s" % (type(e).__name__, e, where)


def error_line(msg):
    import re
    m = re.search(r"\(line (\d+)\)", msg or "")
    return int(m.group(1)) if m else None


def exec_module(compiled, ns, budget):
    """Execute module-level code of a compiled script into ns."""
    return run_call(compiled.filename, lambda: exec(compiled.code, ns), (), budget)
