"""Enemy AI. Uses the same RobotAPI/BaseAPI as players, so fog, costs and ranges apply equally.

Levels (difficulty): 0 passive turtle, 1 slow expansion + small waves, 2 balanced waves + turrets,
3 scouting/harassment/focus fire/upgrades, 4 adaptive counters + flanking.
Styles: rusher / turtle / economist modify thresholds.
"""
import math

from .api import BaseAPI, RobotAPI
from .defs import CLASSES

STYLES = ("rusher", "turtle", "economist")
MILITARY = ("defender", "advanced", "scout")


def run_team(sim, tid):
    if sim.config.get("ai_off"):
        return
    from . import api as _api
    lvl = sim.diff["ai_level"]
    react = sim.diff["ai_react"]
    mem = sim.ai_state.setdefault(("ai", tid), dict(style=sim.config.get("ai_style") or STYLES[sim.seed % 3],
                                                    phase="mass", wave=0, seen={}, turret_sites=[]))
    if "ai_level" in sim.config:
        lvl = sim.config["ai_level"]
    if sim.tick % react == 0:
        _commander(sim, tid, lvl, mem)
    for r in sorted((x for x in sim.robots.values() if x.team == tid), key=lambda x: x.id):
        # reaction delay only applies to combat units; economy units act every tick
        if r.cls in ("defender", "advanced", "scout") and (sim.tick + r.id) % react != 0:
            continue
        api = RobotAPI(sim, r)
        try:
            _unit(sim, api, r, lvl, mem)
        except Exception as e:  # AI must never crash the sim
            sim.log("AI error: %s" % e, r.id, "warn")


def _style_adj(mem):
    s = mem["style"]
    return dict(rusher=dict(wave=-2, turrets=-1, miners=-1, start=-150),
                turtle=dict(wave=+2, turrets=+2, miners=0, start=+250),
                economist=dict(wave=+1, turrets=0, miners=+2, start=+100))[s]


def _commander(sim, tid, lvl, mem):
    base = BaseAPI(sim, tid)
    adj = _style_adj(mem)
    t = sim.tick
    c = base.count
    # observe the opponent (shared vision) for adaptation
    seen = mem["seen"]
    foes = _team_foes(sim, tid)
    for f in foes:
        seen[f.cls] = max(seen.get(f.cls, 0), sum(1 for g in foes if g.cls == f.cls))
    miners_t = [2, 3, 4, 5, 6][lvl] + adj["miners"]
    turrets_t = max(0, [0, 0, 2, 4, 5][lvl] + adj["turrets"])
    def_t = min(14, 2 + t // (500 - 60 * lvl) + (1 if mem["style"] == "rusher" else 0))
    if lvl == 0:
        def_t = 2
    if lvl == 4:
        if seen.get("scout", 0) >= 3:
            turrets_t += 2
        if seen.get("turret", 0) >= 3:
            mem["prefer_support"] = True
    queue = base.queue
    def want(cls, n):
        return c(cls) + queue.count(cls) < n
    if want("miner", miners_t):
        base.build_robot("miner")
    elif lvl >= 2 and want("builder", 1):
        base.build_robot("builder")
    elif want("defender", def_t):
        base.build_robot("defender")
    elif lvl >= 3 and want("scout", 1 + (1 if lvl == 4 else 0)):
        base.build_robot("scout")
    elif lvl >= 3 and want("support", min(3, 1 + c("defender") // 4 + (1 if mem.get("prefer_support") else 0))):
        base.build_robot("support")
    elif lvl >= 4 and base.credits > 320 and want("advanced", 3):
        base.build_robot("advanced")
    mem["turrets_t"] = turrets_t
    if lvl >= 2 and base.researching is None and base.credits > 260:
        order = ["armor", "damage", "speed", "capacity", "energy", "vision"] if mem.get("prefer_support") \
            else ["damage", "armor", "capacity", "speed", "energy", "vision"]
        for name in order:
            if base.research(name):
                break
    army = sum(c(k) for k in MILITARY)
    wave = max(3, [99, 4, 5, 6, 6][lvl] + adj["wave"])
    if lvl >= 1:
        if mem["phase"] == "mass" and army >= wave and t >= [0, 700, 500, 450, 400][lvl] + adj["start"]:
            mem["phase"] = "attack"
            mem["wave"] += 1
            mem["attack_size"] = army
        elif mem["phase"] == "attack" and army < max(2, mem.get("attack_size", 4) * 0.4):
            mem["phase"] = "mass"


def _team_foes(sim, tid):
    out = []
    for r in sim.robots.values():
        if r.team != tid and sim.is_visible(tid, r.x, r.y):
            out.append(type("F", (), dict(cls=r.cls, id=r.id, x=r.x, y=r.y, kind="robot"))())
    for s in sim.structures.values():
        if s.team != tid and sim.is_visible(tid, s.x, s.y):
            out.append(type("F", (), dict(cls=s.kind, id=s.id, x=s.x, y=s.y, kind="structure"))())
    return out


def _flee_or_charge(api, r):
    if api.energy < 18:
        if api.at_hq():
            api.recharge()
        else:
            api.retreat()
        return True
    return False


def _unit(sim, api, r, lvl, mem):
    if _flee_or_charge(api, r):
        return
    cls = r.cls
    if cls == "miner":
        _miner(sim, api, r, lvl)
    elif cls in ("defender", "advanced"):
        _fighter(sim, api, r, lvl, mem)
    elif cls == "scout":
        _scout(sim, api, r, lvl, mem)
    elif cls == "builder":
        _builder(sim, api, r, lvl, mem)
    elif cls == "support":
        _support(sim, api, r, lvl, mem)
    elif cls == "transport":
        api.retreat()


def _danger_near(api, radius=6):
    return [e for e in api.enemies() if e.kind == "robot" and e.cls in MILITARY and e.distance <= radius] + \
           [e for e in api.enemies() if e.cls == "turret" and e.distance <= 7]


def _miner(sim, api, r, lvl):
    if lvl >= 2 and _danger_near(api, 5):
        api.retreat()
        return
    full = api.cargo >= api.capacity * 0.9
    if full or (api.cargo > 0 and not api.known_resources()):
        if api.at_hq() and api.cargo > 0:
            api.deposit()
        else:
            api.retreat()
        return
    ores = api.known_resources()
    if not ores:
        wp = r.memory.get("wp")
        if not wp or math.hypot(api.x - wp[0], api.y - wp[1]) < 3 or sim.tick % 150 == 0:
            wp = _nearest_walkable(sim, (sim.rng.randrange(2, sim.size - 2), sim.rng.randrange(2, sim.size - 2)))
            r.memory["wp"] = wp
        api.move_to(*wp)
        return
    # spread miners across nodes
    ore = ores[(r.id) % min(len(ores), 3)] if len(ores) > 1 else ores[0]
    if max(abs(ore.x - api.x), abs(ore.y - api.y)) <= 1:
        api.mine(ore)
    else:
        api.approach(ore, 1)


def _rally(sim, r, back=4):
    hq = sim.own_hq(r.team)
    ex, ey = sim.hq_pos.get(1 - r.team, (hq.x, hq.y))
    ang = math.atan2(ey - hq.y, ex - hq.x)
    x = int(round(hq.x + back * math.cos(ang)))
    y = int(round(hq.y + back * math.sin(ang)))
    for d in range(0, 5):
        for dx in range(-d, d + 1):
            for dy in range(-d, d + 1):
                if sim.walkable(x + dx, y + dy):
                    return (x + dx, y + dy)
    return (hq.x, hq.y)


def _pick_target(api, lvl, within):
    foes = [e for e in api.team_enemies() if e.distance <= within]
    robots = [e for e in foes if e.kind == "robot"]
    pool = robots or [e for e in foes if e.cls != "wall"] or foes
    if not pool:
        return None
    if lvl >= 3:
        return min(pool, key=lambda e: (e.health, e.distance))
    return min(pool, key=lambda e: e.distance)


def _fighter(sim, api, r, lvl, mem):
    hpfrac = api.health / api.max_health
    if lvl >= 2 and hpfrac < 0.3:
        api.retreat()
        return
    mode_attack = mem["phase"] == "attack" and lvl >= 1
    aggro = 10 if mode_attack else 8
    tgt = _pick_target(api, lvl, aggro)
    if tgt is not None:
        near_base = sim.dist_to_hq_edge(r) <= 12
        if not (mode_attack or near_base) and lvl < 2 and tgt.distance > 6:
            tgt = None
    if tgt is not None:
        if tgt.distance <= api.attack_range + (1 if tgt.kind == "hq" else 0):
            api.attack(tgt)
        else:
            api.approach(tgt, max(1, int(api.attack_range) - 1))
        return
    if mode_attack:
        ex, ey = sim.hq_pos[1 - r.team]
        dx = 1 if api.x < ex else -1
        dy = 1 if api.y < ey else -1
        goal = (ex - 4 * dx, ey - 4 * dy)
        if not sim.walkable(*goal):
            goal = _nearest_walkable(sim, goal)
        if lvl >= 4 and mem.get("wave", 0) % 2 == 0:
            # flank: aim via side waypoint on even waves
            way = (ex - 4 * dx, ey + 8 * dy * -1)
            if sim.in_bounds(*way) and sim.walkable(*way) and math.hypot(api.x - way[0], api.y - way[1]) > 6 \
                    and not r.memory.get("flanked"):
                goal = way
            else:
                r.memory["flanked"] = True
        api.move_to(*goal)
    else:
        rx, ry = _rally(sim, r)
        if math.hypot(api.x - rx, api.y - ry) > 3:
            api.move_to(rx, ry)


def _nearest_walkable(sim, goal):
    gx, gy = goal
    for d in range(0, 8):
        for dx in range(-d, d + 1):
            for dy in range(-d, d + 1):
                if sim.walkable(gx + dx, gy + dy):
                    return (gx + dx, gy + dy)
    return goal


def _scout(sim, api, r, lvl, mem):
    if lvl < 3:
        rx, ry = _rally(sim, r, 5)
        if math.hypot(api.x - rx, api.y - ry) > 3:
            api.move_to(rx, ry)
        tgt = api.nearest_enemy()
        if tgt and tgt.distance <= api.attack_range:
            api.attack(tgt)
        return
    danger = _danger_near(api, 5)
    if danger and api.health < api.max_health * 0.7:
        api.retreat()
        return
    soft = [e for e in api.team_enemies() if e.kind == "robot" and e.cls in ("miner", "builder", "support", "transport")]
    if soft:
        t = min(soft, key=lambda e: e.distance)
        guarded = any(math.hypot(m.x - t.x, m.y - t.y) < 5 for m in api.team_enemies()
                      if m.cls in ("defender", "advanced", "turret"))
        if not guarded:
            if t.distance <= api.attack_range:
                api.attack(t)
            else:
                api.approach(t, 1)
            return
    wp = r.memory.get("wp")
    if not wp or math.hypot(api.x - wp[0], api.y - wp[1]) < 3 or sim.tick % 120 == 0:
        wp = (sim.rng.randrange(2, sim.size - 2), sim.rng.randrange(2, sim.size - 2))
        wp = _nearest_walkable(sim, wp)
        r.memory["wp"] = wp
    api.move_to(*wp)


def _builder(sim, api, r, lvl, mem):
    hq = sim.own_hq(r.team)
    # repair damaged structures first
    for s in sim.structures.values():
        if s.team == r.team and s.built and s.hp < s.max_hp * 0.6:
            if math.hypot(s.x - api.x, s.y - api.y) <= 2.2:
                from .api import _sview
                api.repair(_sview(s))
            else:
                api.move_to(*_nearest_walkable(sim, (s.x, s.y + 1)))
            return
    have = sum(1 for s in sim.structures.values() if s.team == r.team and s.kind == "turret")
    job = r.job and sim.structures.get(r.job["sid"])
    if job is not None and not job.built:
        api.build(job.kind, job.x, job.y)
        return
    if have < mem.get("turrets_t", 0) and sim.teams[r.team].credits >= 60:
        ex, ey = sim.hq_pos.get(1 - r.team, (hq.x, hq.y))
        ang = math.atan2(ey - hq.y, ex - hq.x) + (have % 3 - 1) * 0.55
        site = (int(round(hq.x + (5 + have // 3) * math.cos(ang))), int(round(hq.y + (5 + have // 3) * math.sin(ang))))
        site = _nearest_walkable(sim, site)
        if math.hypot(site[0] - api.x, site[1] - api.y) > 2.2:
            api.move_to(*_nearest_walkable(sim, (site[0], site[1] + 1)))
        else:
            api.build("turret", *site)
    elif lvl >= 3 and sim.teams[r.team].credits >= 40 and \
            not any(s.kind == "solar" and s.team == r.team for s in sim.structures.values()):
        site = _nearest_walkable(sim, (hq.x + 3, hq.y + 3))
        if math.hypot(site[0] - api.x, site[1] - api.y) > 2.2:
            api.move_to(*site)
        else:
            api.build("solar", *site)
    else:
        rx, ry = _rally(sim, r, 2)
        if math.hypot(api.x - rx, api.y - ry) > 3:
            api.move_to(rx, ry)


def _support(sim, api, r, lvl, mem):
    hurt = [a for a in api.allies() if a.health < a.max_health * 0.85]
    if hurt:
        t = min(hurt, key=lambda a: a.health / a.max_health)
        if t.distance <= 2:
            api.repair(t)
        else:
            api.approach(t, 1)
        return
    rx, ry = _rally(sim, r, 3)
    if math.hypot(api.x - rx, api.y - ry) > 3:
        api.move_to(rx, ry)
