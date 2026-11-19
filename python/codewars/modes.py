"""Game modes: scenario configs, objective evaluation, scoring."""
import math

from . import defs, worldgen
from .defs import DIFFICULTY

MODES = {
    "robot_wars": dict(title="Robot Wars", blurb="Program an army and destroy the enemy HQ before they destroy yours."),
    "base_commander": dict(title="Base Commander", blurb="Grow an economy and base: income, structures and population targets."),
    "exploration": dict(title="Exploration", blurb="Uncover the map and recover signal beacons with scouts."),
    "factory": dict(title="Factory Automation", blurb="Build a refinery chain and hit the alloy quota."),
    "racing": dict(title="Robot Racing", blurb="Hit every checkpoint in order in the fewest ticks."),
    "sandbox": dict(title="Sandbox", blurb="No objectives: experiment freely with all classes."),
}


def build_config(mode, difficulty="normal", world="ironvale", seed=1, advanced_mode=False, overrides=None):
    d = DIFFICULTY[difficulty]
    cfg = dict(mode=mode, difficulty=difficulty, world=world, seed=seed, advanced_mode=advanced_mode)
    start = [dict(cls="miner"), dict(cls="miner"), dict(cls="scout"), dict(cls="builder"), dict(cls="defender")]
    if mode == "robot_wars":
        cfg.update(enemy=True, start_units=start + [dict(cls="miner", team=1), dict(cls="miner", team=1),
                                                     dict(cls="defender", team=1), dict(cls="builder", team=1)],
                   max_ticks=3200)
        cfg["objectives"] = [dict(type="destroy_enemy_hq", title="Destroy the enemy HQ"),
                             dict(type="protect_hq", title="Keep your HQ alive")]
    elif mode == "base_commander":
        target = [600, 900, 1400, 2000, 2800][d["index"] - 1]
        cfg.update(enemy=False, start_units=[dict(cls="miner"), dict(cls="builder"), dict(cls="scout")],
                   max_ticks=2400,
                   objectives=[dict(type="earn", amount=target, title="Deliver %d ore" % target),
                               dict(type="structures", amount=[2, 3, 4, 5, 6][d["index"] - 1], title="Build structures"),
                               dict(type="population", amount=[5, 6, 8, 10, 12][d["index"] - 1], title="Reach population")])
    elif mode == "exploration":
        pct = [50, 60, 70, 80, 88][d["index"] - 1]
        w = worldgen.generate_world(world, d["map_size"], seed)
        beacons = _pick_beacons(w, 3 + d["index"], seed)
        cfg.update(enemy=False, start_units=[dict(cls="scout"), dict(cls="scout"), dict(cls="scout")],
                   max_ticks=1400, beacons=beacons,
                   objectives=[dict(type="explore", percent=pct, title="Explore %d%% of the map" % pct),
                               dict(type="beacons", amount=len(beacons), title="Recover all beacons")])
    elif mode == "factory":
        q = [8, 14, 22, 32, 45][d["index"] - 1]
        cfg.update(enemy=False, credits=defs.DIFFICULTY[difficulty]["start_credits"] + 150,
                   start_units=[dict(cls="miner"), dict(cls="miner"), dict(cls="builder")],
                   max_ticks=2600,
                   objectives=[dict(type="alloy", amount=q, title="Produce %d alloy" % q),
                               dict(type="structure_kind", kind="refinery", amount=1, title="Build a refinery")])
    elif mode == "racing":
        w = worldgen.generate_world(world, d["map_size"], seed)
        cps = _pick_checkpoints(w, 5 + d["index"], seed)
        cfg.update(enemy=False, start_units=[dict(cls="scout")], checkpoints=cps, max_ticks=1200,
                   objectives=[dict(type="checkpoints", amount=len(cps), title="Pass all %d checkpoints" % len(cps))])
    else:  # sandbox
        foe = bool((overrides or {}).get("enemy", False))
        enemy_units = [dict(cls="miner", team=1), dict(cls="defender", team=1), dict(cls="builder", team=1)]
        cfg.update(enemy=foe, start_units=start + (enemy_units if foe else []), credits=2000,
                   max_ticks=10 ** 7, scale_time=False, objectives=[])
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if k != "enemy" or mode != "sandbox"})
    return cfg


def _free_reach(w):
    """Reachable tiles from the first HQ that are not on/next to ore nodes or inside the HQ footprints."""
    ore = {(o["x"], o["y"]) for o in w["ore"]}
    hq = {(h[0] + dx, h[1] + dy) for h in w["hq"] for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    h0 = w["hq"][0]
    start = (h0[0] + 2, h0[1] + 2)          # just outside the 3x3 HQ footprint (always grass)
    reach = worldgen.reachable_set(w["grid"], start, frozenset(ore | hq))
    return {p for p in reach if not any((p[0] + dx, p[1] + dy) in ore for dx in (-1, 0, 1) for dy in (-1, 0, 1))}


def _pick_beacons(w, n, seed):
    import random
    rng = random.Random(seed + 77)
    reach = _free_reach(w)
    far = [p for p in reach if math.hypot(p[0] - w["hq"][0][0], p[1] - w["hq"][0][1]) > 10]
    rng.shuffle(far)
    out = []
    for p in far:
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 8 for q in out):
            out.append(p)
        if len(out) >= n:
            break
    return [list(p) for p in out]


def _pick_checkpoints(w, n, seed):
    import random
    rng = random.Random(seed + 33)
    reach = list(_free_reach(w))
    reach.sort()
    rng.shuffle(reach)
    pts = []
    for p in reach:
        if math.hypot(p[0] - w["hq"][0][0], p[1] - w["hq"][0][1]) < 6:
            continue
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 7 for q in pts):
            pts.append(p)
        if len(pts) >= n:
            break
    return [list(p) for p in pts]


def evaluate(sim):
    """Update objective status and decide result."""
    if sim.result is not None:
        return
    t0 = sim.teams[0]
    st = []
    done_all = True
    for o in sim.objectives:
        typ = o["type"]
        cur, goal, ok = 0, 1, False
        if typ == "destroy_enemy_hq":
            ok = sim.has_enemy and sim.own_hq(1) is None
            cur, goal = (1 if ok else 0), 1
        elif typ == "protect_hq":
            ok = sim.own_hq(0) is not None
            cur, goal = (1 if ok else 0), 1
        elif typ == "earn":
            cur, goal = t0.stats["ore_delivered"], o["amount"]
            ok = cur >= goal
        elif typ == "structures":
            cur = sum(1 for s in sim.structures.values() if s.team == 0 and s.built and s.kind != "hq")
            goal = o["amount"]
            ok = cur >= goal
        elif typ == "structure_kind":
            cur = sum(1 for s in sim.structures.values() if s.team == 0 and s.built and s.kind == o["kind"])
            goal = o["amount"]
            ok = cur >= goal
        elif typ == "population":
            cur, goal = sum(1 for r in sim.robots.values() if r.team == 0), o["amount"]
            ok = cur >= goal
        elif typ == "explore":
            tot = sim.size * sim.size
            walk = sum(1 for y in range(sim.size) for x in range(sim.size) if sim.grid[y][x] not in defs.BLOCKED_TERRAIN)
            cur = round(100.0 * sum(1 for y in range(sim.size) for x in range(sim.size)
                                    if t0.explored[y * sim.size + x] and sim.grid[y][x] not in defs.BLOCKED_TERRAIN) / max(1, walk), 1)
            goal = o["percent"]
            ok = cur >= goal
        elif typ == "beacons":
            cur, goal = t0.stats["beacons"], o["amount"]
            ok = cur >= goal
        elif typ == "alloy":
            cur, goal = t0.stats["alloy_made"], o["amount"]
            ok = cur >= goal
        elif typ == "checkpoints":
            cur, goal = t0.stats["checkpoints"], o["amount"]
            ok = cur >= goal
        elif typ == "kill":
            cur, goal = t0.stats["kills"], o["amount"]
            ok = cur >= goal
        st.append(dict(title=o.get("title", typ), current=cur, goal=goal, done=ok, type=typ))
        if typ != "protect_hq":
            done_all = done_all and ok
    sim.objective_status = st
    if sim.mode in ("robot_wars",) or (sim.has_enemy and sim.objectives):
        if sim.own_hq(0) is None:
            sim.result = dict(winner=1, reason="Your HQ was destroyed", tick=sim.tick)
            return
        if sim.own_hq(1) is None:
            sim.result = dict(winner=0, reason="Enemy HQ destroyed", tick=sim.tick)
            return
    elif sim.objectives and done_all:
        sim.result = dict(winner=0, reason="All objectives complete", tick=sim.tick)
        return
    if sim.tick >= sim.max_ticks and sim.objectives:
        if sim.has_enemy:
            a, b = _score(sim, 0), _score(sim, 1)
            sim.result = dict(winner=0 if a >= b else 1, reason="Time limit: decided on score (%d vs %d)" % (a, b),
                              tick=sim.tick)
        else:
            sim.result = dict(winner=None, reason="Time limit reached before the objectives were met", tick=sim.tick)


def _score(sim, team):
    t = sim.teams[team]
    hq = sim.own_hq(team)
    return int(t.stats["damage_dealt"] + t.stats["ore_delivered"] * 0.5 + (hq.hp if hq else 0) +
               sum(1 for r in sim.robots.values() if r.team == team) * 20)


def stars(sim):
    r = sim.result
    if not r or r.get("winner") != 0:
        return 0
    s = 1
    frac = r["tick"] / max(1, sim.max_ticks)
    if frac < 0.7:
        s += 1
    if sim.mode == "robot_wars":
        t = sim.teams[0]
        if t.stats["losses"] <= max(3, t.stats["produced"] * 0.5):
            s += 1
    else:
        if frac < 0.45 and sim.teams[0].stats["script_errors"] == 0:
            s += 1
    return min(3, s)
