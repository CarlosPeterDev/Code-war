"""Interactive lessons. Every lesson runs the learner's real Python in the sandbox:
'func' lessons call a function against tests; 'sim' lessons run a short real simulation and check
what the learner's script actually did to the game objects."""
import math

from . import puzzles, sandbox
from . import modes
from . import sim as simmod


# --------------------------------------------------------------------------- sim predicates
def _chk_move(sim):
    r = next(r for r in sim.robots.values() if r.cls == "scout")
    start = sim.config["_start"]
    d = math.hypot(r.x - start[0], r.y - start[1])
    return d >= 8, "Your scout moved %.1f tiles from its start (need 8+)." % d


def _chk_mine(sim):
    got = sim.teams[0].stats["ore_delivered"]
    return got >= 40, "Ore delivered to the HQ: %d (need 40+)." % got


def _chk_recharge(sim):
    r = next(r for r in sim.robots.values() if r.cls == "miner")
    return r.energy >= r.energy * 0 + 70, "Miner energy is %.0f (need 70+ after recharging)." % r.energy


def _chk_fight(sim):
    k = sim.teams[0].stats["kills"]
    return k >= 1, "Enemy robots destroyed: %d (need 1)." % k


def _chk_memory(sim):
    mem = [r.memory.get("steps", 0) for r in sim.robots.values() if r.team == 0]
    return bool(mem) and min(mem) >= 25, "robot.memory['steps'] values: %s (need 25+ for every robot)." % mem


def _chk_rally(sim):
    rally = sim.teams[0].memory.get("rally")
    if not rally:
        return False, "robot.team_memory['rally'] was never set."
    rx, ry = rally
    near = sum(1 for r in sim.robots.values() if r.team == 0 and math.hypot(r.x - rx, r.y - ry) <= 3.5)
    total = sum(1 for r in sim.robots.values() if r.team == 0)
    return near >= total and total >= 3, "%d of %d robots reached the rally point %s." % (near, total, tuple(rally))


def _chk_group(sim):
    groups = {r.cls: r.group for r in sim.robots.values() if r.team == 0}
    ok = groups.get("miner") == "workers" and groups.get("scout") == "eyes"
    return ok, "Groups assigned: %s (need miner='workers', scout='eyes')." % groups


def _setup_fight(sim):
    hx, hy = sim.hq_pos[0]
    spot = sim._free_tile_near(hx + 5, hy + 3, 0, 3)
    sim.spawn_robot(1, "miner", spot[0], spot[1])


CHECKS = {"move": _chk_move, "mine": _chk_mine, "recharge": _chk_recharge, "fight": _chk_fight,
          "memory": _chk_memory, "rally": _chk_rally, "group": _chk_group}

_SCOUT = [dict(cls="scout")]
_MINERS = [dict(cls="miner"), dict(cls="miner")]
_TRIO = [dict(cls="scout"), dict(cls="miner"), dict(cls="defender")]

LESSONS = [
 dict(id="l01", section="Python basics", title="Variables and numbers", kind="func", func="energy_percent",
      text="A variable stores a value: `energy = 40`. Numbers support + - * / // % and **. `//` is whole-number division.\n\nTask: write energy_percent(energy, max_energy) that returns the energy as a whole-number percentage (e.g. 30 of 120 -> 25).",
      starter="def energy_percent(energy, max_energy):\n    return 0\n",
      tests=[((30, 120), 25), ((100, 100), 100), ((0, 80), 0), ((45, 90), 50)]),
 dict(id="l02", section="Python basics", title="Data types", kind="func", func="describe",
      text="Common types: int (3), float (2.5), str ('scout'), bool (True), list ([1, 2]), dict ({'hp': 5}). `isinstance(x, int)` tests a type. Careful: True is also an int, so test bool first!\n\nTask: describe(x) returns 'bool', 'int', 'float', 'str', 'list' or 'dict'.",
      starter="def describe(x):\n    return ''\n",
      tests=[((True,), "bool"), ((3,), "int"), ((2.5,), "float"), (("hi",), "str"), (([1],), "list"), (({"a": 1},), "dict")]),
 dict(id="l03", section="Python basics", title="Conditions: if / elif / else", kind="func", func="should_retreat",
      text="Conditions choose what to do: `if health < 30:` ... `elif energy < 15:` ... `else:`. Combine tests with `and`, `or`, `not`.\n\nTask: should_retreat(health, energy) is True when health is below 30 OR energy is below 15.",
      starter="def should_retreat(health, energy):\n    return False\n",
      tests=[((20, 80), True), ((90, 10), True), ((90, 80), False), ((29, 14), True), ((30, 15), False)]),
 dict(id="l04", section="Python basics", title="Loops: for and while", kind="func", func="count_class",
      text="`for item in items:` repeats once per item. `while condition:` repeats while the condition holds (make sure it can end!). `range(5)` gives 0..4.\n\nTask: count_class(robots, cls) returns how many dicts in `robots` have robot['cls'] == cls.",
      starter="def count_class(robots, cls):\n    n = 0\n    # loop over robots here\n    return n\n",
      tests=[(([{"cls": "miner"}, {"cls": "scout"}, {"cls": "miner"}], "miner"), 2), (([], "miner"), 0), (([{"cls": "scout"}], "miner"), 0)]),
 dict(id="l05", section="Python basics", title="Functions and return values", kind="func", func="damage_after_armor",
      text="`def name(arguments):` defines a function; `return` hands back a result. In Code Wars, damage taken = damage * 20 / (20 + armor), but never less than 1.\n\nTask: damage_after_armor(damage, armor) returns that value rounded to 2 decimals (use round(x, 2)).",
      starter="def damage_after_armor(damage, armor):\n    return 0\n",
      tests=[((14, 6), 10.77), ((10, 0), 10.0), ((1, 100), 1), ((20, 20), 10.0)]),
 dict(id="l06", section="Python basics", title="Lists", kind="func", func="healthiest",
      text="Lists hold ordered items: `robots = [3, 1, 2]`, `robots[0]`, `len(robots)`, `robots.append(4)`, slicing `robots[1:]`. `max(list, key=...)` finds the biggest by a rule.\n\nTask: healthiest(robots) takes dicts {'id', 'hp'} and returns the id of the robot with the most hp (None if the list is empty).",
      starter="def healthiest(robots):\n    return None\n",
      tests=[(([{"id": 1, "hp": 30}, {"id": 2, "hp": 80}, {"id": 3, "hp": 55}],), 2), (([],), None), (([{"id": 9, "hp": 1}],), 9)]),
 dict(id="l07", section="Python basics", title="Dictionaries", kind="func", func="tally",
      text="A dict maps keys to values: `d = {'miner': 2}`, `d['scout'] = 1`, `d.get('x', 0)`, `for k, v in d.items():`.\n\nTask: tally(names) returns a dict counting how often each name occurs.",
      starter="def tally(names):\n    return {}\n",
      tests=[((["a", "b", "a"],), {"a": 2, "b": 1}), (([],), {}), ((["x", "x", "x"],), {"x": 3})]),
 dict(id="l08", section="Python basics", title="Strings", kind="func", func="report",
      text="Strings hold text: `name.upper()`, `len(name)`, `name.split(',')`, `'-'.join(parts)`. f-strings build text: `f\"{name}: {hp} HP\"`. (str.format() is disabled in the sandbox - use f-strings.)\n\nTask: report(name, hp) returns text like 'SCOUT: 40 HP' (name in capitals).",
      starter="def report(name, hp):\n    return ''\n",
      tests=[(("scout", 40), "SCOUT: 40 HP"), (("Miner", 70), "MINER: 70 HP")]),
 dict(id="l09", section="Robot control", title="Move your first robot", kind="sim", check="move", ticks=90,
      units=_SCOUT, starter="def update(robot):\n    # update() runs once per tick for every robot.\n    # Make the scout walk away from the HQ with robot.move_to(x, y).\n    pass\n",
      text="Your script defines `update(robot)`. The game calls it once per tick (4 ticks = 1 second). `robot.move_to(x, y)` plans a path and the robot follows it, spending energy.\n\nTask: send the scout at least 8 tiles away from where it starts. Tip: x, y = robot.pos; robot.move_to(x + 9, y + 9) - if that tile is blocked it returns False, so try another direction."),
 dict(id="l10", section="Robot control", title="Mine and deliver ore", kind="sim", check="mine", ticks=240, units=_MINERS,
      starter="def update(robot):\n    # 1. If cargo is full: go to the HQ and robot.deposit()\n    # 2. Otherwise: find ore with robot.known_resources() and robot.mine(node)\n    pass\n",
      text="Miners extract ore with `robot.mine(node)` when ADJACENT to the node, then must carry it to the HQ and call `robot.deposit()` (1 ore = 1 credit). Use `robot.approach(node, 1)` to walk next to a node, `robot.retreat()` to walk home, `robot.at_hq()` to know you've arrived.\n\nTask: get 40 ore delivered."),
 dict(id="l11", section="Robot control", title="Energy management", kind="sim", check="recharge", ticks=40, units=[dict(cls="miner")],
      low_energy=12,
      starter="def update(robot):\n    # Energy is spent by moving and acting. Near the HQ, robot.recharge() restores 24 per call.\n    pass\n",
      text="Every move and action costs energy; at 0 a robot is stuck. Near the HQ (or a solar panel) `robot.recharge()` restores 24 energy per call - but it uses your action for that tick.\n\nTask: this miner starts nearly empty. Recharge it above 70 energy. Hint: check `robot.energy < robot.max_energy` and `robot.at_hq()`."),
 dict(id="l12", section="Robot control", title="Combat basics", kind="sim", check="fight", ticks=150, units=[dict(cls="defender")], enemy=True, setup="fight",
      starter="def update(robot):\n    # robot.team_enemies() lists enemies seen by your whole team (shared vision).\n    # attack only works within robot.attack_range; use robot.approach(target, 2) to close in.\n    pass\n",
      text="Armed robots (scout, defender, advanced) use `robot.attack(target)` when the target is within `robot.attack_range` and the weapon is ready. `robot.team_enemies()` gives enemies that anyone on your team can see, nearest first.\n\nTask: destroy the lone enemy miner parked near your base."),
 dict(id="l13", section="Automation", title="Memory: remembering between ticks", kind="sim", check="memory", ticks=30, units=_TRIO,
      starter="def update(robot):\n    # robot.memory is a dict that survives between ticks.\n    # Count how many ticks this robot has run in robot.memory['steps'].\n    pass\n",
      text="Local variables vanish after update() returns, but `robot.memory` (a dict) persists. This is how robots follow multi-step plans: store a state like `robot.memory['state'] = 'delivering'`.\n\nTask: make every robot count its ticks in robot.memory['steps'] (reach 25 or more)."),
 dict(id="l14", section="Automation", title="Groups and roles", kind="sim", check="group", ticks=5, units=[dict(cls="miner"), dict(cls="scout")],
      starter="def update(robot):\n    # robot.set_group('name') labels a robot. Scripts can later be assigned per group.\n    pass\n",
      text="Groups let you give a squad its own behaviour. `robot.set_group('workers')` labels a robot; in the editor you can assign a script to a group.\n\nTask: put miners in group 'workers' and scouts in group 'eyes' (check robot.cls)."),
 dict(id="l15", section="Multi-robot coordination", title="Team memory and rally points", kind="sim", check="rally", ticks=140, units=_TRIO,
      starter="def update(robot):\n    # robot.team_memory is shared by every robot on your team.\n    # Store a rally point in robot.team_memory['rally'] = (x, y) and send everyone there.\n    pass\n",
      text="`robot.team_memory` is one dict shared by your whole team - the simplest way to coordinate. One robot can publish a target and everyone reads it.\n\nTask: choose a walkable rally tile near your HQ, store it in robot.team_memory['rally'], and move all robots to within 3 tiles of it. Tip: hx, hy = robot.hq; the tile (hx + 3, hy + 2) is always clear."),
]
BY_ID = {l["id"]: l for l in LESSONS}
_PUBLIC = ("id", "section", "title", "kind", "text", "starter")


def get_lessons():
    out = []
    for l in LESSONS:
        d = {k: l[k] for k in _PUBLIC}
        d["tests"] = len(l.get("tests", [])) if l["kind"] == "func" else 1
        out.append(d)
    return out


def run_lesson(lid, source):
    l = BY_ID.get(lid)
    if l is None:
        return dict(ok=False, message="unknown lesson")
    if l["kind"] == "func":
        return puzzles.check_function(source, l["func"], l["tests"])
    problems = sandbox.validate_source(source, "main.py")
    if problems:
        return dict(ok=False, message=problems[0]["message"], line=problems[0]["line"], logs=[], problems=problems)
    cfg = modes.build_config("sandbox", "beginner", "ironvale", 7,
                             overrides=dict(start_units=l["units"], enemy=l.get("enemy", False), ai_off=True,
                                            credits=300, max_ticks=10 ** 7))
    sim = simmod.Sim(cfg)
    scout = [r for r in sim.robots.values() if r.team == 0]
    cfg["_start"] = (scout[0].x, scout[0].y) if scout else (0, 0)
    if l.get("low_energy"):
        for r in sim.robots.values():
            r.energy = l["low_energy"]
    if l.get("setup") == "fight":
        _setup_fight(sim)
    sim.set_scripts({"main.py": source}, {"default": "main.py"})
    sim.step(l["ticks"])
    ok, msg = CHECKS[l["check"]](sim)
    errs = [x["text"] for x in sim.logs if x["level"] == "error"]
    logs = [x["text"] for x in list(sim.logs)[-12:] if x["level"] in ("print", "error")]
    if not ok and errs:
        msg = errs[0] + "  -  " + msg
    return dict(ok=ok, message=("Mission complete! " if ok else "Not yet: ") + msg, logs=logs, passed=1 if ok else 0, total=1,
                results=[])
