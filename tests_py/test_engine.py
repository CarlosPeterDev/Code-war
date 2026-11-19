import json
import math

import pytest

from codewars import analysis, api, api_spec, bridge, defs, modes, puzzles, templates, worldgen
from codewars import sim as S


def make(mode="sandbox", diff="normal", seed=1, world="ironvale", **over):
    cfg = modes.build_config(mode, diff, world, seed, overrides=over or None)
    return S.Sim(cfg)


def free_adjacent(sim, r):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        x, y = r.x + dx, r.y + dy
        if sim.walkable(x, y) and (x, y) not in sim.occ:
            return x, y
    raise AssertionError("no free adjacent tile")


def only(sim, cls, team=0):
    return [r for r in sim.robots.values() if r.team == team and r.cls == cls]


# ------------------------------------------------------------- pathfinding / world
def test_pathfinding_avoids_obstacles_and_blocked_tiles():
    grid = [[0] * 10 for _ in range(10)]
    for y in range(9):
        grid[y][5] = defs.ROCK
    p = worldgen.find_path(grid, set(), (0, 0), (9, 0))
    assert p and p[-1] == (9, 0) and all(grid[y][x] != defs.ROCK for x, y in p)
    assert any(y == 9 for _, y in p), "must go around through the gap"
    assert worldgen.find_path(grid, {(5, 9)}, (0, 0), (9, 0)) is None


def test_pathfinding_no_corner_cutting():
    grid = [[0] * 3 for _ in range(3)]
    grid[0][1] = grid[1][0] = defs.ROCK
    assert worldgen.find_path(grid, set(), (0, 0), (1, 1)) is None


def test_sand_is_costlier_than_grass():
    grid = [[0, 1, 1, 1, 0]] + [[0] * 5 for _ in range(2)]
    p = worldgen.find_path(grid, set(), (0, 0), (4, 0))
    assert any(y > 0 for _, y in p), "path should detour around slow sand"


@pytest.mark.parametrize("world", list(defs.WORLDS))
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_worlds_are_connected_and_have_ore(world, seed):
    w = worldgen.generate_world(world, 32, seed)
    reach = worldgen.reachable_set(w["grid"], w["hq"][0])
    assert w["hq"][1] in reach
    for hq in w["hq"]:
        assert sum(1 for o in w["ore"] if math.hypot(o["x"] - hq[0], o["y"] - hq[1]) <= 11) >= 3


def test_world_generation_is_deterministic():
    assert worldgen.generate_world("ironvale", 32, 5)["grid"] == worldgen.generate_world("ironvale", 32, 5)["grid"]
    assert worldgen.generate_world("ironvale", 32, 5)["grid"] != worldgen.generate_world("ironvale", 32, 6)["grid"]


# ------------------------------------------------------------- scripts drive real objects
def test_script_moves_a_real_robot():
    sim = make()
    sim.set_scripts({"main.py": "def update(robot):\n    robot.move_to(robot.hq[0] + 6, robot.hq[1])\n"}, {"default": "main.py"})
    r = only(sim, "scout")[0]
    start = (r.x, r.y)
    sim.step(30)
    assert (r.x, r.y) != start and r.energy < sim.stat(r, "energy")


def test_movement_costs_energy_and_stops_at_zero():
    sim = make()
    r = only(sim, "scout")[0]
    r.energy = 3.0
    reach = worldgen.reachable_set(sim.grid, (r.x, r.y), sim.blocked)
    tx, ty = max(reach, key=lambda p: math.hypot(p[0] - r.x, p[1] - r.y))
    sim.set_scripts({"main.py": "def update(robot):\n    robot.move_to(%d, %d)\n" % (tx, ty)}, {"default": "main.py"})
    sim.step(40)
    assert r.energy < 0.5
    pos = (r.x, r.y)
    sim.step(10)
    assert (r.x, r.y) == pos


def test_mining_and_deposit_produce_credits():
    sim = make()
    sim.set_scripts(templates.starter_scripts(), templates.STARTER_ASSIGN)
    c0 = sim.teams[0].credits
    sim.step(300)
    st = sim.teams[0].stats
    assert st["ore_mined"] > 100 and st["ore_delivered"] > 100
    assert sim.teams[0].credits > c0 - 0 or st["credits_spent"] > 0


def test_miner_class_restrictions_and_errors_are_reported():
    sim = make()
    scout = only(sim, "scout")[0]
    a = api.RobotAPI(sim, scout)
    node = next(iter(sim.ores.values()))
    assert a.mine(api._oview(node)) is False and "cannot mine" in a.last_error
    assert a.build("turret", scout.x + 1, scout.y) is False and "cannot build" in a.last_error
    with pytest.raises(TypeError):
        a.move_to("a", 1)
    with pytest.raises(TypeError):
        a.attack("enemy")


def test_one_action_per_tick():
    sim = make(enemy=True)
    d = only(sim, "defender")[0]
    en = only(sim, "defender", team=1)
    assert en, "enemy has a defender"
    e = en[0]
    e.x, e.y = d.x + 2, d.y
    sim.occ[(e.x, e.y)] = e.id
    sim._update_visibility()
    a = api.RobotAPI(sim, d)
    view = api._rview(sim, e, d)
    assert a.attack(view) is True
    assert a.attack(view) is False


# ------------------------------------------------------------- combat math
def test_damage_formula_and_armor():
    sim = make(enemy=True)
    t = only(sim, "defender", team=1)[0]
    hp = t.hp
    sim._damage_robot(t, 14, 0)
    expected = max(1.0, 14 * 20.0 / (20.0 + sim.stat(t, "armor")))
    assert hp - t.hp == pytest.approx(expected)
    scout = only(sim, "scout")[0]
    h2 = scout.hp
    sim._damage_robot(scout, 1, 1)
    assert h2 - scout.hp >= 1.0, "minimum damage is 1"


def test_tech_changes_stats():
    sim = make()
    d = only(sim, "defender")[0]
    base = sim.stat(d, "damage")
    sim.teams[0].tech["damage"] = 2
    assert sim.stat(d, "damage") == pytest.approx(base * 1.3)
    sim.teams[0].tech["armor"] = 1
    assert sim.stat(d, "armor") == defs.CLASSES["defender"]["armor"] + 2


def test_kill_removes_robot_and_counts():
    sim = make(enemy=True)
    v = only(sim, "miner", team=1)[0]
    sim._damage_robot(v, 10 ** 6, 0)
    assert v.id not in sim.robots and sim.teams[0].stats["kills"] == 1 and sim.teams[1].stats["losses"] == 1


def test_turret_fires_at_enemies():
    sim = make(enemy=True)
    hq = sim.own_hq(0)
    t = sim._add_structure(0, "turret", hq.x + 4, hq.y)
    t.built, t.hp = True, t.max_hp
    foe = only(sim, "miner", team=1)[0]
    sim.occ.pop((foe.x, foe.y))
    foe.x, foe.y = t.x + 3, t.y
    sim.occ[(foe.x, foe.y)] = foe.id
    hp = foe.hp
    sim.step(3)
    assert foe.hp < hp


def test_hq_destruction_ends_robot_wars():
    sim = make("robot_wars", "normal", 1)
    hq = sim.own_hq(1)
    sim._damage_structure(hq, 10 ** 6, 0)
    sim.step(1)
    assert sim.result and sim.result["winner"] == 0


# ------------------------------------------------------------- structures / production / research
def test_builder_constructs_structure_and_spends_credits():
    sim = make(credits=500)
    b = only(sim, "builder")[0]
    tx, ty = free_adjacent(sim, b)
    sim.set_scripts({"main.py": "def update(robot):\n    robot.build('wall', %d, %d)\n" % (tx, ty)}, {"class:builder": "main.py"})
    cr = sim.teams[0].credits
    sim.step(8)
    walls = [s for s in sim.structures.values() if s.kind == "wall"]
    assert walls and walls[0].built and sim.teams[0].credits == cr - defs.STRUCTURES["wall"]["cost"]
    assert not sim.walkable(walls[0].x, walls[0].y)


def test_build_requires_credits_and_range():
    sim = make(credits=5)
    a = api.RobotAPI(sim, only(sim, "builder")[0])
    r = only(sim, "builder")[0]
    tx, ty = free_adjacent(sim, r)
    assert a.build("turret", tx, ty) is False and "credits" in a.last_error
    sim.teams[0].credits = 500
    assert a.build("turret", r.x + 9, r.y) is False and "too far" in a.last_error


def test_production_queue_and_population_cap():
    sim = make()
    base = api.BaseAPI(sim, 0)
    n0 = base.population
    assert base.build_robot("miner")
    sim.step(defs.CLASSES["miner"]["build_time"] + 2)
    assert base.population == n0 + 1
    with pytest.raises(ValueError):
        base.build_robot("tank")
    sim.teams[0].credits = 0
    assert base.build_robot("miner") is False


def test_research_applies_after_delay_and_costs():
    sim = make()
    base = api.BaseAPI(sim, 0)
    sim.teams[0].credits = 1000
    assert base.research("armor") and base.researching == "armor"
    assert base.research("damage") is False
    sim.step(defs.RESEARCH_TICKS + 1)
    assert base.tech["armor"] == 1 and sim.teams[0].credits == 1000 - 100


def test_refinery_converts_ore_to_alloy():
    sim = make()
    hq = sim.own_hq(0)
    ref = sim._add_structure(0, "refinery", hq.x + 4, hq.y)
    ref.built, ref.hp = True, ref.max_hp
    m = only(sim, "miner")[0]
    sim.occ.pop((m.x, m.y))
    m.x, m.y = ref.x + 1, ref.y
    sim.occ[(m.x, m.y)] = m.id
    m.cargo = 20
    assert api.RobotAPI(sim, m).deposit()
    assert sim.teams[0].alloy == 10


def test_support_repairs_and_shares_energy():
    sim = make()
    s = only(sim, "support") or [sim.spawn_robot(0, "support")]
    s = s[0]
    d = only(sim, "defender")[0]
    sim.occ.pop((d.x, d.y))
    d.x, d.y = s.x + 1, s.y
    sim.occ[(d.x, d.y)] = d.id
    d.hp -= 40
    d.energy = 10
    a = api.RobotAPI(sim, s)
    assert a.repair(api._rview(sim, d, s)) and d.hp == pytest.approx(defs.CLASSES["defender"]["hp"] - 30)
    sim.step(1)
    assert a.share_energy(api._rview(sim, d, s), 10) and d.energy >= 19.9


def test_fog_of_war_hides_unseen_enemies():
    sim = make("robot_wars", "normal", 1)
    r = only(sim, "scout")[0]
    assert api.RobotAPI(sim, r).enemies() == []
    assert not sim.is_visible(0, *sim.hq_pos[1])


# ------------------------------------------------------------- determinism / save-load
def _state(sim):
    return (sim.tick, sorted((r.id, r.cls, r.x, r.y, round(r.hp, 3), round(r.energy, 3), r.cargo) for r in sim.robots.values()),
            sorted((s.id, s.kind, round(s.hp, 3)) for s in sim.structures.values()),
            sim.teams[0].credits, sim.result)


NORAND = {k: v for k, v in templates.starter_scripts().items() if k != "miner.py"}
NORAND["miner.py"] = templates.TEMPLATES["miner.py"][1]


def test_simulation_is_deterministic():
    def run():
        s = make("robot_wars", "normal", 4)
        s.set_scripts(templates.starter_scripts(), templates.STARTER_ASSIGN)
        s.step(250)
        return _state(s)
    assert run() == run()


def test_save_load_roundtrip_continues_identically():
    a = make("robot_wars", "easy", 2)
    a.set_scripts(templates.starter_scripts(), templates.STARTER_ASSIGN)
    a.step(120)
    blob = json.loads(json.dumps(a.to_dict()))
    b = S.Sim.from_dict(blob)
    assert _state(a) == _state(b)
    a.step(60)
    b.step(60)
    assert _state(a) == _state(b)


def test_save_preserves_scripts_memory_and_stats():
    a = make()
    a.set_scripts({"main.py": "def update(robot):\n    robot.memory['n'] = robot.memory.get('n', 0) + 1\n"}, {"default": "main.py"})
    a.step(5)
    b = S.Sim.from_dict(json.loads(json.dumps(a.to_dict())))
    assert b.scripts == a.scripts
    assert all(r.memory.get("n") == 5 for r in b.robots.values() if r.team == 0)
    assert b.teams[0].stats == a.teams[0].stats


# ------------------------------------------------------------- script errors & budgets inside the game
def test_script_runtime_error_is_logged_and_game_continues():
    sim = make()
    sim.set_scripts({"main.py": "def update(robot):\n    x = 1 / 0\n"}, {"default": "main.py"})
    sim.step(3)
    assert sim.teams[0].stats["script_errors"] > 0
    assert any(l["level"] == "error" and "ZeroDivisionError" in l["text"] for l in sim.logs)
    assert sim.tick == 3


def test_infinite_loop_script_cannot_freeze_the_game():
    sim = make()
    sim.set_scripts({"main.py": "def update(robot):\n    while True:\n        pass\n"}, {"default": "main.py"})
    sim.step(2)
    assert sim.tick == 2 and sim.teams[0].stats["budget_overruns"] > 0


def test_syntax_error_script_reports_and_robots_idle():
    sim = make()
    sim.set_scripts({"main.py": "def update(robot):\nmove\n"}, {"default": "main.py"})
    assert sim.script_problems["main.py"]
    sim.step(2)
    assert any("has errors" in l["text"] for l in sim.logs)


def test_script_cannot_reach_engine_internals():
    sim = make()
    sim.set_scripts({"main.py": "def update(robot):\n    robot._s.teams[0].credits = 10**9\n"}, {"default": "main.py"})
    assert sim.script_problems["main.py"] and sim.teams[0].credits < 10 ** 6


def test_script_assignment_priority_robot_group_class_default():
    sim = make()
    sim.set_scripts({"a.py": "def update(robot):\n    pass\n", "b.py": "def update(robot):\n    pass\n",
                     "c.py": "def update(robot):\n    pass\n", "d.py": "def update(robot):\n    pass\n"},
                    {"default": "a.py", "class:miner": "b.py", "group:g": "c.py"})
    m = only(sim, "miner")[0]
    assert sim.script_for(m) == "b.py"
    m.group = "g"
    assert sim.script_for(m) == "c.py"
    sim.assign["robot:%d" % m.id] = "d.py"
    assert sim.script_for(m) == "d.py"


def test_debugger_returns_trace_and_variables_without_changing_game():
    sim = make()
    sim.set_scripts({"main.py": "def update(robot):\n    n = robot.energy\n    robot.log('e')\n    robot.move_to(robot.x + 1, robot.y)\n"},
                    {"default": "main.py"})
    sim.step(2)
    r = only(sim, "scout")[0]
    before = _state(sim)
    d = sim.debug_robot(r.id, [4])
    assert d["ok"] and 2 in d["trace"] and d["snapshots"] and "n" in d["snapshots"][0]["variables"]
    assert _state(sim) == before


# ------------------------------------------------------------- difficulty, modes, missions
def test_idle_player_loses_on_every_difficulty():
    for diff in ("beginner", "easy", "normal", "hard", "expert"):
        sim = make("robot_wars", diff, 3)
        sim.set_scripts({}, {})
        sim.step(sim.max_ticks)
        assert sim.result and sim.result["winner"] == 1, diff


def test_difficulty_scales_resources_and_ai():
    d = defs.DIFFICULTY
    order = ["beginner", "easy", "normal", "hard", "expert"]
    assert [d[k]["start_credits"] for k in order] == sorted([d[k]["start_credits"] for k in order], reverse=True)
    assert [d[k]["ai_level"] for k in order] == [0, 1, 2, 3, 4]
    assert [d[k]["line_budget"] for k in order] == sorted([d[k]["line_budget"] for k in order], reverse=True)


def test_starter_scripts_win_beginner_robot_wars():
    wins = 0
    for seed in (1, 2):
        sim = make("robot_wars", "beginner", seed)
        sim.set_scripts(templates.starter_scripts(), templates.STARTER_ASSIGN)
        sim.step(sim.max_ticks)
        wins += 1 if sim.result and sim.result["winner"] == 0 else 0
    assert wins == 2


def test_valid_script_does_not_automatically_win_on_hard():
    """A trivially valid script (does nothing) never wins; the AI must be beaten by real play."""
    sim = make("robot_wars", "hard", 2)
    sim.set_scripts({"main.py": "def update(robot):\n    robot.log('hi')\n"}, {"default": "main.py"})
    sim.step(sim.max_ticks)
    assert sim.result["winner"] == 1


RACER = {"main.py": "def update(robot):\n    cp = robot.checkpoint\n    if cp:\n        robot.move_to(cp[0], cp[1])\n"}


def test_racing_mode_completes_with_checkpoint_follower():
    sim = make("racing", "easy", 2)
    sim.set_scripts(RACER, {"default": "main.py"})
    assert len(sim.checkpoints) >= 5
    sim.step(sim.max_ticks)
    assert sim.result and sim.result["winner"] == 0 and sim.teams[0].stats["checkpoints"] == len(sim.checkpoints)


def test_racing_fails_without_script():
    sim = make("racing", "easy", 2)
    assert len(sim.checkpoints) >= 5
    sim.set_scripts({}, {})
    sim.step(sim.max_ticks)
    assert sim.result["winner"] is None


EXPLORE = '''
def update(robot):
    mem = robot.memory
    wp = mem.get('wp')
    if wp is None or robot.distance_to(wp[0], wp[1]) < 3 or not robot.moving:
        import random
        for _ in range(30):
            x = random.randint(1, 30)
            y = random.randint(1, 30)
            if robot.can_walk(x, y) and robot.move_to(x, y):
                mem['wp'] = (x, y)
                break
    for b in robot.beacons():
        if not b['found']:
            robot.move_to(b['x'], b['y'])
'''


def test_exploration_mode_completes_with_scouts():
    sim = make("exploration", "beginner", 1)
    assert len(sim.beacons) >= 3
    sim.set_scripts({"main.py": EXPLORE}, {"default": "main.py"})
    sim.step(sim.max_ticks)
    assert sim.result and sim.result["winner"] == 0, sim.objective_status


COMMANDER_ECON = '''
def commander(base):
    if base.count('miner') + base.queue.count('miner') < 4:
        base.build_robot('miner')
    elif base.count('builder') + base.queue.count('builder') < 2:
        base.build_robot('builder')
    elif base.count('transport') + base.queue.count('transport') < 1:
        base.build_robot('transport')
'''
BUILD_MORE = '''
def update(robot):
    hx, hy = robot.hq
    mem = robot.memory
    spots = [(hx + 3, hy + 2), (hx + 3, hy - 2), (hx - 3, hy + 2), (hx - 3, hy - 2), (hx + 2, hy + 3), (hx - 2, hy + 3)]
    i = mem.get('i', 0)
    if i >= len(spots):
        return
    x, y = spots[i]
    if robot.distance_to(x, y) > 1.6:
        if not (robot.move_to(x, y + 1) or robot.move_to(x, y - 1)):
            mem['i'] = i + 1
        return
    here = [s for s in robot.structures() if s.pos == (x, y)]
    if here:
        if here[0].built:
            mem['i'] = i + 1
        else:
            robot.build('wall', x, y)
        return
    if not robot.build('wall', x, y):
        if 'blocked' in robot.last_error or 'occupied' in robot.last_error:
            mem['i'] = i + 1
'''


def test_base_commander_mode_completes():
    sim = make("base_commander", "beginner", 1)
    miner = templates.TEMPLATES["miner.py"][1]
    sim.set_scripts({"commander.py": COMMANDER_ECON, "miner.py": miner, "builder.py": BUILD_MORE, "scout.py": "def update(robot):\n    pass\n"},
                    {"commander": "commander.py", "class:miner": "miner.py", "class:builder": "builder.py", "class:scout": "scout.py", "class:transport": "scout.py"})
    sim.step(sim.max_ticks)
    assert sim.result and sim.result["winner"] == 0, sim.objective_status


FACTORY_BUILD = '''
def update(robot):
    hx, hy = robot.hq
    x, y = hx + 3, hy + 2
    if robot.team_memory.get('ref'):
        return
    if robot.distance_to(x, y) > 2:
        robot.move_to(x, y + 1)
        return
    here = [s for s in robot.structures() if s.cls == 'refinery' and s.pos == (x, y)]
    if here and here[0].built:
        robot.team_memory['ref'] = (x, y)
        return
    robot.build('refinery', x, y)
'''
FACTORY_MINER = '''
def update(robot):
    if robot.energy < 20:
        if robot.at_hq():
            robot.recharge()
        else:
            robot.retreat()
        return
    ref = robot.team_memory.get('ref')
    if robot.cargo >= robot.capacity - 4:
        if ref:
            rx, ry = ref
            if max(abs(rx - robot.x), abs(ry - robot.y)) <= 1:
                robot.deposit()
            else:
                robot.move_to(rx + 1, ry + 1) or robot.move_to(rx, ry + 1)
        else:
            robot.retreat()
        return
    ore = robot.known_resources()
    if ore:
        n = ore[0]
        if max(abs(n.x - robot.x), abs(n.y - robot.y)) <= 1:
            robot.mine(n)
        else:
            robot.approach(n, 1)
'''


def test_factory_mode_completes_with_refinery_chain():
    sim = make("factory", "beginner", 1)
    sim.set_scripts({"b.py": FACTORY_BUILD, "m.py": FACTORY_MINER}, {"class:builder": "b.py", "class:miner": "m.py"})
    sim.step(sim.max_ticks)
    assert sim.result and sim.result["winner"] == 0, sim.objective_status


def test_objective_status_reports_progress():
    sim = make("base_commander", "normal", 1)
    sim.step(1)
    assert len(sim.objective_status) == 3 and all("goal" in o for o in sim.objective_status)


def test_sandbox_mode_has_no_objectives_and_never_ends():
    sim = make("sandbox")
    sim.step(50)
    assert sim.result is None and sim.objectives == []


# ------------------------------------------------------------- analysis
def test_post_match_analysis_explains_outcome():
    sim = make("robot_wars", "hard", 2)
    sim.set_scripts({"main.py": "def update(robot):\n    robot.log('x')\n"}, {"default": "main.py"})
    sim.step(sim.max_ticks)
    rep = analysis.analyze(sim)
    texts = " ".join(i["text"] for i in rep["items"])
    assert rep["items"] and "HQ" in texts and rep["stars"] == 0 and ("Damage dealt" in texts or "dealt no damage" in texts) and any(i["kind"] == "bad" for i in rep["items"])


def test_analysis_flags_script_errors():
    sim = make()
    sim.set_scripts({"main.py": "def update(robot):\n    x = 1/0\n"}, {"default": "main.py"})
    sim.step(5)
    assert any(i["kind"] == "bad" and "errors" in i["text"] for i in analysis.analyze(sim)["items"])


# ------------------------------------------------------------- API docs coverage
def _public(cls):
    return {n for n in dir(cls) if not n.startswith("_")}


def test_every_api_member_is_documented_and_vice_versa():
    spec = api_spec.get_spec()
    for owner, cls in (("robot", api.RobotAPI), ("base", api.BaseAPI), ("entity", api.View)):
        assert {s["name"] for s in spec if s["owner"] == owner} == _public(cls), owner


def test_api_spec_entries_are_complete():
    for s in api_spec.get_spec():
        assert s["description"] and s["returns"] and s["cost"] and s["signature"] and s["example"]
        if s["kind"] == "method":
            for p in s["params"]:
                assert p["type"] and p["valid"]


def test_all_api_examples_execute_in_the_sandbox():
    for s in api_spec.get_spec():
        if s["owner"] == "entity":
            sim = make("sandbox")
        else:
            sim = make("sandbox")
        sim.set_scripts({"ex.py": s["example"]}, {"default": "ex.py"} if s["owner"] != "base" else {"commander": "ex.py"})
        assert not sim.script_problems, (s["signature"], sim.script_problems)
        sim.step(3)
        errs = [l for l in sim.logs if l["level"] == "error"]
        assert not errs, (s["signature"], errs[:1])


# ------------------------------------------------------------- puzzles and bridge
SOLUTIONS = {
    "total_ore": "def total_ore(nodes):\n    t = 0\n    for n in nodes:\n        t += n['amount']\n    return t\n",
    "closest_point": "def closest(points, me):\n    best = None\n    bd = None\n    for p in points:\n        d = (p[0]-me[0])**2 + (p[1]-me[1])**2\n        if bd is None or d < bd:\n            best, bd = p, d\n    return best\n",
    "fizzbuzz": "def signal(n):\n    out = []\n    for i in range(1, n+1):\n        if i % 15 == 0:\n            out.append('FizzBuzz')\n        elif i % 3 == 0:\n            out.append('Fizz')\n        elif i % 5 == 0:\n            out.append('Buzz')\n        else:\n            out.append(str(i))\n    return out\n",
    "palindrome": "def is_mirror(text):\n    s = ''.join(c for c in text.lower() if c.isalpha())\n    return s == s[::-1]\n",
    "word_count": "def word_count(text):\n    d = {}\n    for w in text.lower().split():\n        d[w] = d.get(w, 0) + 1\n    return d\n",
    "primes": "def primes_upto(n):\n    return [p for p in range(2, n+1) if all(p % d for d in range(2, int(p**0.5)+1))]\n",
    "trips": "def trips_needed(amounts, capacity):\n    return sum((a + capacity - 1) // capacity for a in amounts)\n",
    "balance": "def split_squads(ids, k):\n    out = [[] for _ in range(k)]\n    for i, x in enumerate(ids):\n        out[i % k].append(x)\n    return out\n",
    "region": "def region_size(grid, start):\n    h = len(grid)\n    w = len(grid[0])\n    stack = [start]\n    seen = {start}\n    while stack:\n        x, y = stack.pop()\n        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):\n            nx = x + dx\n            ny = y + dy\n            if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] == 0 and (nx, ny) not in seen:\n                seen.add((nx, ny))\n                stack.append((nx, ny))\n    return len(seen)\n",
    "shortest": "def shortest_steps(grid, start, goal):\n    h = len(grid)\n    w = len(grid[0])\n    q = [(start, 0)]\n    seen = {start}\n    i = 0\n    while i < len(q):\n        (x, y), d = q[i]\n        i += 1\n        if (x, y) == goal:\n            return d\n        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):\n            nx = x + dx\n            ny = y + dy\n            if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] == 0 and (nx, ny) not in seen:\n                seen.add((nx, ny))\n                q.append(((nx, ny), d + 1))\n    return -1\n",
    "focus_fire": "def pick_target(enemies, range_):\n    c = [e for e in enemies if e['distance'] <= range_]\n    if not c:\n        return None\n    return min(c, key=lambda e: (e['health'], e['distance'], e['id']))['id']\n",
}


@pytest.mark.parametrize("pid", [p["id"] for p in puzzles.PUZZLES])
def test_puzzle_reference_solution_passes_and_starter_fails(pid):
    assert puzzles.run_puzzle(pid, SOLUTIONS[pid])["ok"], puzzles.run_puzzle(pid, SOLUTIONS[pid])
    assert not puzzles.run_puzzle(pid, puzzles.find(pid)["starter"])["ok"]


def test_puzzle_runner_rejects_unsafe_and_looping_code():
    assert not puzzles.run_puzzle("total_ore", "import os\ndef total_ore(n):\n    return 0\n")["ok"]
    r = puzzles.run_puzzle("total_ore", "def total_ore(n):\n    while True:\n        pass\n")
    assert not r["ok"] and "budget" in r["results"][0]["got"].lower() or "BudgetExceeded" in str(r)


def test_every_template_is_valid_python_for_the_sandbox():
    for t in templates.get_templates():
        sim = make()
        sim.set_scripts({t["name"]: t["source"]}, {})
        assert not sim.script_problems, t["name"]


def test_bridge_full_flow():
    cat = json.loads(bridge.catalog())
    assert set(cat["difficulties"]) == {"beginner", "easy", "normal", "hard", "expert"}
    assert len(json.loads(bridge.api_reference())) > 80
    g = json.loads(bridge.new_game(json.dumps(dict(mode="robot_wars", difficulty="easy", seed=2)),
                                   json.dumps(templates.starter_scripts()), json.dumps(templates.STARTER_ASSIGN)))
    assert g["world"]["size"] == defs.DIFFICULTY["easy"]["map_size"] and g["snapshot"]["robots"]
    snap = json.loads(bridge.step(30))
    assert snap["tick"] == 30
    rid = next(r["id"] for r in snap["robots"] if r["team"] == 0 and r["cls"] == "miner")
    info = json.loads(bridge.robot_info(rid))
    assert "mine" in info["api"] and "mine" in info["abilities"] and "attack" not in info["api"]
    blob = bridge.save_game()
    snap2 = json.loads(bridge.load_game(blob))["snapshot"]
    assert snap2["tick"] == 30
    assert json.loads(bridge.analysis_report())["items"]
    assert json.loads(bridge.validate("def f(:\n  pass"))[0]["severity"] == "error"
