"""Programming challenges and function-based lesson checks, executed in the sandbox."""
import copy

from . import sandbox


def _fizz(n):
    out = []
    for i in range(1, n + 1):
        out.append("FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else str(i))
    return out


def _primes(n):
    return [p for p in range(2, n + 1) if all(p % d for d in range(2, int(p ** 0.5) + 1))]


def _bfs(grid, start, goal):
    from collections import deque
    h, w = len(grid), len(grid[0])
    q, seen = deque([(start, 0)]), {start}
    while q:
        (x, y), d = q.popleft()
        if (x, y) == goal:
            return d
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] == 0 and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append(((nx, ny), d + 1))
    return -1


def _region(grid, start):
    h, w = len(grid), len(grid[0])
    stack, seen = [start], {start}
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] == 0 and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))
    return len(seen)


G1 = [[0, 0, 0, 0], [1, 1, 0, 1], [0, 0, 0, 0], [0, 1, 1, 0]]
G2 = [[0, 1, 0], [0, 1, 0], [0, 1, 0]]
G3 = [[0, 0, 0], [0, 1, 0], [0, 0, 0]]

# id, title, level, topic, statement, func, starter, tests [(args, expected)], hint
PUZZLES = [
 dict(id="total_ore", title="Total Ore", level=1, topic="loops", func="total_ore",
      statement="`nodes` is a list of dicts like {'x': 3, 'y': 4, 'amount': 120}. Return the total of all 'amount' values.",
      starter="def total_ore(nodes):\n    # your code here\n    return 0\n",
      tests=[(([{"amount": 10}, {"amount": 5}],), 15), (([],), 0), (([{"amount": 120}],), 120)],
      hint="Loop over nodes and add node['amount'] to a running total."),
 dict(id="closest_point", title="Closest Ore", level=1, topic="algorithms", func="closest",
      statement="Given a list of (x, y) tuples and your position me=(x, y), return the tuple closest to me (straight-line). Return None for an empty list.",
      starter="def closest(points, me):\n    return None\n",
      tests=[(([(5, 5), (1, 1), (9, 0)], (0, 0)), (1, 1)), (([], (0, 0)), None), (([(3, 4), (4, 3)], (3, 3)), (3, 4))],
      hint="Compare (px-mx)**2 + (py-my)**2; no need for a square root."),
 dict(id="fizzbuzz", title="Signal Codes", level=1, topic="conditions", func="signal",
      statement="Return a list for 1..n: 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for both, otherwise the number as a string.",
      starter="def signal(n):\n    return []\n",
      tests=[((5,), _fizz(5)), ((15,), _fizz(15)), ((0,), [])], hint="Check the multiple-of-15 case first."),
 dict(id="palindrome", title="Mirror Message", level=1, topic="strings", func="is_mirror",
      statement="Return True if the text reads the same forwards and backwards, ignoring case and spaces.",
      starter="def is_mirror(text):\n    return False\n",
      tests=[(("Never odd or even",), True), (("robot",), False), (("",), True), (("A man a plan a canal Panama",), True)],
      hint="Build a cleaned string with only lowercase letters, then compare it with its reverse (s[::-1])."),
 dict(id="word_count", title="Radio Chatter", level=2, topic="dicts", func="word_count",
      statement="Return a dict mapping each lowercase word in the text to how many times it appears. Words are separated by spaces.",
      starter="def word_count(text):\n    return {}\n",
      tests=[(("a b a",), {"a": 2, "b": 1}), (("Go GO go",), {"go": 3}), (("",), {})],
      hint="text.lower().split() gives the words; use d[w] = d.get(w, 0) + 1."),
 dict(id="primes", title="Prime Frequencies", level=2, topic="loops", func="primes_upto",
      statement="Return all prime numbers <= n in ascending order.",
      starter="def primes_upto(n):\n    return []\n",
      tests=[((10,), _primes(10)), ((2,), [2]), ((1,), []), ((50,), _primes(50))],
      hint="A number p is prime if no d in 2..sqrt(p) divides it."),
 dict(id="trips", title="Haul Planner", level=2, topic="functions", func="trips_needed",
      statement="A transport carries `capacity` ore per trip. Given a list of ore amounts, return the minimum number of trips if each trip serves ONE node (a trip cannot combine nodes).",
      starter="def trips_needed(amounts, capacity):\n    return 0\n",
      tests=[(([100, 30], 40), 4), (([], 10), 0), (([40], 40), 1), (([41], 40), 2)],
      hint="Per node you need ceil(amount / capacity): use (a + capacity - 1) // capacity."),
 dict(id="balance", title="Squad Split", level=2, topic="lists", func="split_squads",
      statement="Split the list of robot ids into k squads by dealing them out round-robin (first id to squad 0, second to squad 1, ...). Return a list of k lists.",
      starter="def split_squads(ids, k):\n    return []\n",
      tests=[(([1, 2, 3, 4, 5], 2), [[1, 3, 5], [2, 4]]), (([], 3), [[], [], []]), (([7], 1), [[7]])],
      hint="Create k empty lists, then use i % k as the squad index."),
 dict(id="region", title="Safe Zone", level=3, topic="algorithms", func="region_size",
      statement="`grid` is a list of rows; 0 = open, 1 = wall. Return how many open tiles are connected (4-directional) to `start` = (x, y), including the start tile.",
      starter="def region_size(grid, start):\n    return 0\n",
      tests=[((G1, (0, 0)), _region(G1, (0, 0))), ((G2, (0, 0)), 3), ((G3, (0, 0)), 8)],
      hint="Use a stack or queue and a set of visited tiles (flood fill)."),
 dict(id="shortest", title="Shortest Route", level=3, topic="algorithms", func="shortest_steps",
      statement="Same grid format (0 open, 1 wall). Return the minimum number of 4-directional steps from start to goal, or -1 if unreachable.",
      starter="def shortest_steps(grid, start, goal):\n    return -1\n",
      tests=[((G1, (0, 0), (3, 3)), _bfs(G1, (0, 0), (3, 3))), ((G2, (0, 0), (2, 0)), -1), ((G3, (0, 0), (2, 2)), 4)],
      hint="Breadth-first search from the start; keep (tile, steps) in a list used as a queue."),
 dict(id="focus_fire", title="Focus Fire", level=3, topic="algorithms", func="pick_target",
      statement="`enemies` is a list of dicts {'id', 'health', 'distance'}. Pick the id to attack: lowest health among enemies with distance <= range_; ties broken by smaller distance, then smaller id. Return None if none are in range.",
      starter="def pick_target(enemies, range_):\n    return None\n",
      tests=[(([{"id": 1, "health": 30, "distance": 3}, {"id": 2, "health": 10, "distance": 4}], 5), 2),
             (([{"id": 1, "health": 10, "distance": 6}], 5), None),
             (([{"id": 4, "health": 10, "distance": 3}, {"id": 3, "health": 10, "distance": 3}], 5), 3)],
      hint="Filter first, then min() with a tuple key (health, distance, id)."),
]


def get_puzzles():
    return [dict(id=p["id"], title=p["title"], level=p["level"], topic=p["topic"], statement=p["statement"],
                 starter=p["starter"], hint=p["hint"], tests=len(p["tests"])) for p in PUZZLES]


def find(pid):
    for p in PUZZLES:
        if p["id"] == pid:
            return p
    return None


def check_function(source, func, tests, line_budget=400000):
    """Run `func(*args)` for each test in the sandbox. Returns dict(ok, passed, total, results, problems)."""
    problems = sandbox.validate_source(source, "solution.py")
    if problems:
        return dict(ok=False, passed=0, total=len(tests), results=[], problems=problems,
                    message=problems[0]["message"])
    comp = sandbox.CompiledScript("solution.py", source)
    import random
    ns = sandbox.make_namespace(lambda m: None, random.Random(1))
    b = sandbox.Budget(line_budget, 2.0, check_memory=False)
    ok, res = sandbox.exec_module(comp, ns, b)
    if not ok:
        return dict(ok=False, passed=0, total=len(tests), results=[], problems=[], message=res)
    fn = ns.get(func)
    if not callable(fn):
        return dict(ok=False, passed=0, total=len(tests), results=[], problems=[],
                    message="Your code must define a function named %s." % func)
    results, passed = [], 0
    for args, expected in tests:
        b = sandbox.Budget(line_budget, 2.0, check_memory=False)
        ok, got = sandbox.run_call(comp.filename, fn, copy.deepcopy(args), b)
        good = ok and got == expected
        passed += 1 if good else 0
        results.append(dict(args=repr(args)[:120], expected=repr(expected)[:80],
                            got=(repr(got)[:80] if ok else str(got)[:160]), passed=good))
    return dict(ok=passed == len(tests), passed=passed, total=len(tests), results=results, problems=[],
                message="All tests passed!" if passed == len(tests) else "%d of %d tests passed." % (passed, len(tests)))


def run_puzzle(pid, source):
    p = find(pid)
    if p is None:
        return dict(ok=False, message="unknown puzzle")
    return check_function(source, p["func"], p["tests"])
