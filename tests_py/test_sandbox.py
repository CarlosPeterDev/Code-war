import random

import pytest

from codewars import sandbox


def run(src, lines=20000, secs=0.5, fn=None, args=()):
    c = sandbox.CompiledScript("t.py", src)
    if c.code is None:
        return "REJECTED", c.problems[0]["message"]
    ns = sandbox.make_namespace(lambda m: None, random.Random(1))
    ok, r = sandbox.exec_module(c, ns, sandbox.Budget(lines, secs))
    if not ok:
        return "ERR", r
    if fn:
        ok, r = sandbox.run_call(c.filename, ns[fn], args, sandbox.Budget(lines, secs))
        return ("OK", r) if ok else ("ERR", r)
    return "OK", ns


@pytest.mark.parametrize("src", [
    "x = ().__class__", "x = f'{[].__class__}'", "x = '{0.__class__}'.format(1)", "import os", "import sys",
    "from os import path", "open('/etc/passwd')", "eval('1')", "exec('1')", "x = getattr(1, 'real')",
    "g = (i for i in [1])\nf = g.gi_frame.f_back.f_globals", "def f():\n    pass\nx = f.__globals__",
    "x = type(1)", "class A:\n    pass", "global x", "x = __import__('os')", "x = globals()",
    "async def f():\n    pass", "x = robot._s", "try:\n    pass\nexcept Exception as e:\n    e.with_traceback(None)",
])
def test_forbidden_constructs_rejected(src):
    assert run(src)[0] == "REJECTED"


@pytest.mark.parametrize("src", [
    "x = 1 << 10**9", "l = [0]*20000\nfor i in range(30):\n    l += l", "l = [0]*20000\nfor i in range(30):\n    l.extend(l)",
    "s = 'a'\nfor i in range(40):\n    s = s + s", "s = 'a'*30000\nx = ''.join([s]*30000)", "x = 'a'.ljust(10**9)",
    "x = ('a'*30000).replace('a', 'b'*30000)", "x = 9**9**9", "x = list(range(10**9))", "x = [0] * 10**9",
    "x = 'ab' * 10**9",
])
def test_resource_bombs_stopped(src):
    kind, msg = run(src)
    assert kind == "ERR" and "BudgetExceeded" in msg


def test_infinite_loop_stopped_by_instruction_budget():
    kind, msg = run("while True:\n    pass", lines=5000)
    assert kind == "ERR" and "instruction budget" in msg


def test_wall_clock_budget():
    kind, msg = run("x = 0\nwhile True:\n    x += 1", lines=10 ** 9, secs=0.05)
    assert kind == "ERR" and "time budget" in msg


def test_recursion_is_caught():
    kind, msg = run("def f(n):\n    return f(n + 1)\nf(0)")
    assert kind == "ERR" and "Recursion" in msg


def test_runtime_error_reports_line_number():
    kind, msg = run("x = 1\ny = x / 0\n")
    assert kind == "ERR" and "ZeroDivisionError" in msg and sandbox.error_line(msg) == 2


def test_syntax_error_reported_with_line():
    c = sandbox.CompiledScript("t.py", "def f(:\n    pass\n")
    assert c.code is None and c.problems[0]["line"] == 1


def test_math_is_trimmed_but_useful():
    assert run("import math\nx = math.sqrt(16)")[0] == "OK"
    assert run("import math\nx = math.factorial(10)")[0] == "ERR"


def test_normal_python_features_work():
    src = '''
import math
def f(n, *, step=1):
    out = []
    for i in range(0, n, step):
        if i % 2 == 0:
            out.append(i * i)
        elif i % 3 == 0:
            out += [i]
        else:
            continue
    return out

def g(d):
    return {k: v for k, v in sorted(d.items())}

def h(s):
    return f"{s.upper()}-{len(s)}"

class_free = (1, 2, 3)
a, *b = class_free
t = 0
while t < 5:
    t += 1
total = sum([1, 2, 3]) + max(4, 5) + min([6, 7]) + abs(-3) + round(2.6) + int('4') + len('abc')
alias = [1]
alias2 = alias
alias2 += [2]
'''
    kind, ns = run(src)
    assert kind == "OK"
    assert ns["f"](10) == [0, 4, 3, 16, 36, 64, 9]
    assert ns["g"]({"b": 1, "a": 2}) == {"a": 2, "b": 1}
    assert ns["h"]("ab") == "AB-2"
    assert ns["t"] == 5 and ns["total"] == 6 + 5 + 6 + 3 + 3 + 4 + 3
    assert ns["alias"] == [1, 2], "list += must keep Python aliasing semantics"
    assert ns["a"] == 1 and ns["b"] == [2, 3]


def test_print_goes_to_log_callback():
    logs = []
    c = sandbox.CompiledScript("t.py", "print('hi', 3)\n")
    ns = sandbox.make_namespace(logs.append, random.Random(1))
    assert sandbox.exec_module(c, ns, sandbox.Budget(1000, 1))[0]
    assert logs == ["hi 3"]


def test_random_is_seeded_and_deterministic():
    a = run("import random\nx = [random.randint(0, 99) for _ in range(5)]")[1]["x"]
    b = run("import random\nx = [random.randint(0, 99) for _ in range(5)]")[1]["x"]
    assert a == b


def test_breakpoint_snapshots_capture_variables():
    c = sandbox.CompiledScript("t.py", "def update(r):\n    a = 5\n    b = a * 2\n    return b\n")
    ns = sandbox.make_namespace(lambda m: None, random.Random(1))
    sandbox.exec_module(c, ns, sandbox.Budget(1000, 1, check_memory=False))
    b = sandbox.Budget(1000, 1, check_memory=False)
    b.breakpoints = {c.filename: {4}}
    ok, res = sandbox.run_call(c.filename, ns["update"], (None,), b)
    assert ok and res == 10
    assert b.snapshots and b.snapshots[0]["variables"]["b"] == "10"
