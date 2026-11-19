"""Deterministic simulation core."""
import math
import random
from collections import deque

from . import defs, sandbox, worldgen
from .defs import CLASSES, COSTS, STRUCTURES, TECH

MAX_POP = 40
LOG_LIMIT = 400
HISTORY_LIMIT = 40


class Team:
    def __init__(self, tid, size, credits):
        self.id = tid
        self.credits = credits
        self.alloy = 0
        self.tech = {k: 0 for k in TECH}
        self.research = None            # [name, remaining]
        self.queues = []                # list of [cls, remaining]
        self.explored = bytearray(size * size)
        self.visible = bytearray(size * size)
        self.memory = {}
        self.stats = dict(damage_dealt=0.0, damage_taken=0.0, kills=0, losses=0, ore_mined=0,
                          ore_delivered=0, credits_spent=0, built=0, produced=0, idle_ticks=0,
                          empty_energy_ticks=0, script_errors=0, budget_overruns=0, alloy_made=0,
                          structures_lost=0, peak_robots=0, robot_ticks=0, repaired=0, beacons=0, checkpoints=0)
        self.lost_by_cause = {}
        self.beacons_found = set()


class Robot:
    def __init__(self, rid, team, cls, x, y):
        self.id, self.team, self.cls = rid, team, cls
        self.x, self.y = x, y
        self.hp = self.energy = 0.0
        self.cargo = 0
        self.path = []
        self.goal = None
        self.mp = 0.0
        self.cd = 0
        self.acted = False
        self.memory = {}
        self.group = ""
        self.ns = None
        self.script_key = None
        self.last_error = ""
        self.history = deque(maxlen=HISTORY_LIMIT)
        self.blocked_ticks = 0
        self.job = None
        self.alive = True
        self.action = "idle"
        self.target = None
        self.facing = 0.0
        self.idle_flag = True
        self.err_count = 0
        self.spawned = 0
        self.checkpoint_idx = 0


class Structure:
    def __init__(self, sid, team, kind, x, y):
        self.id, self.team, self.kind, self.x, self.y = sid, team, kind, x, y
        spec = STRUCTURES.get(kind)
        self.max_hp = defs.HQ_HP if kind == "hq" else spec["hp"]
        self.hp = self.max_hp if kind == "hq" else 1.0
        self.progress = 0.0
        self.built = kind == "hq"
        self.cd = 0
        self.angle = 0.0

    def tiles(self):
        if self.kind == "hq":
            return [(self.x + dx, self.y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        return [(self.x, self.y)]


class Ore:
    def __init__(self, oid, x, y, amount):
        self.id, self.x, self.y, self.amount, self.max_amount = oid, x, y, amount, amount


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


class Sim:
    def __init__(self, config):
        self.config = config
        self.mode = config.get("mode", "sandbox")
        self.diff_name = config.get("difficulty", "normal")
        self.diff = defs.DIFFICULTY[self.diff_name]
        self.seed = config.get("seed", 1)
        self.rng = random.Random(self.seed)
        self.tick = 0
        self.next_id = 1
        self.events = []
        self.logs = deque(maxlen=LOG_LIMIT)
        self.result = None            # None | dict(winner, reason)
        self.advanced_editor = bool(config.get("advanced_mode", False))
        size = config.get("size") or self.diff["map_size"]
        world = worldgen.generate_world(config.get("world", "ironvale"), size, self.seed,
                                        ore_mult=self.diff["ore_mult"] * config.get("ore_mult", 1.0))
        self.size = size
        self.world_id = config.get("world", "ironvale")
        self.grid = world["grid"]
        self.trees = world["trees"]
        self.robots, self.structures, self.ores = {}, {}, {}
        self.blocked = set()
        self.occ = {}
        self.has_enemy = config.get("enemy", self.mode in ("robot_wars", "campaign_war"))
        self.teams = {0: Team(0, size, config.get("credits", self.diff["start_credits"]))}
        if self.has_enemy:
            self.teams[1] = Team(1, size, config.get("enemy_credits", self.diff["start_credits"]))
        self.hq_pos = {0: world["hq"][0], 1: world["hq"][1]}
        for tid in self.teams:
            hx, hy = self.hq_pos[tid]
            self._add_structure(tid, "hq", hx, hy)
        for o in world["ore"]:
            self._add_ore(o["x"], o["y"], o["amount"])
        self.beacons = []
        self.checkpoints = []
        self.scripts = {}
        self.compiled = {}
        self.assign = {}
        self.script_problems = {}
        self.last_logged_error = {}
        self.ai_state = {}
        self.objectives = list(config.get("objectives", []))
        self.max_ticks = int(config.get("max_ticks", defs.MAX_TICKS_DEFAULT) * self.diff["time_mult"]) \
            if config.get("scale_time", True) else int(config.get("max_ticks", defs.MAX_TICKS_DEFAULT))
        self.line_budget = self.diff["line_budget"] * (2 if self.advanced_editor else 1)
        self.robot_time_budget = 0.02
        self.team_time_budget = 0.25
        self.memory_check = config.get("memory_check", True)
        self.player_seen = set()
        self.history_totals = []
        for spec in config.get("start_units", []):
            self.spawn_robot(spec.get("team", 0), spec["cls"], spec.get("x"), spec.get("y"))
        self._setup_mode(config)
        self._update_visibility()
        for t in self.teams.values():
            t.stats["peak_robots"] = len([r for r in self.robots.values() if r.team == t.id])

    # ------------------------------------------------------------ setup
    def _setup_mode(self, config):
        for b in config.get("beacons", []):
            self.beacons.append(dict(id=self._nid(), x=b[0], y=b[1], found=False))
        self.checkpoints = [tuple(c) for c in config.get("checkpoints", [])]
        for b in config.get("extra_ore", []):
            self._add_ore(b[0], b[1], b[2])

    def _nid(self):
        self.next_id += 1
        return self.next_id - 1

    def _add_structure(self, team, kind, x, y):
        s = Structure(self._nid(), team, kind, x, y)
        self.structures[s.id] = s
        for t in s.tiles():
            self.blocked.add(t)
        return s

    def _add_ore(self, x, y, amount):
        o = Ore(self._nid(), x, y, amount)
        self.ores[o.id] = o
        self.blocked.add((x, y))
        return o

    def spawn_robot(self, team, cls, x=None, y=None):
        hx, hy = self.hq_pos[team]
        if x is None:
            spot = self._free_tile_near(hx, hy, 2, 5)
            if spot is None:
                return None
            x, y = spot
        r = Robot(self._nid(), team, cls, x, y)
        r.spawned = self.tick
        self.robots[r.id] = r
        self.occ[(x, y)] = r.id
        r.hp = self.stat(r, "hp")
        r.energy = self.stat(r, "energy")
        self.events.append(dict(t="spawn", id=r.id, x=x, y=y, cls=cls, team=team))
        return r

    def _free_tile_near(self, cx, cy, rmin, rmax):
        cands = []
        for dy in range(-rmax, rmax + 1):
            for dx in range(-rmax, rmax + 1):
                d = max(abs(dx), abs(dy))
                x, y = cx + dx, cy + dy
                if rmin <= d <= rmax and 0 <= x < self.size and 0 <= y < self.size \
                        and self.grid[y][x] not in defs.BLOCKED_TERRAIN \
                        and (x, y) not in self.blocked and (x, y) not in self.occ:
                    cands.append((d, (x, y)))
        if not cands:
            return None
        cands.sort(key=lambda c: (c[0], c[1]))
        return cands[0][1]

    # ------------------------------------------------------------ stats
    def stat(self, r, key):
        base = CLASSES[r.cls][key]
        t = self.teams[r.team].tech
        if key == "hp":
            return base
        if key == "damage":
            return base * (1 + TECH["damage"]["per_level"] * t["damage"])
        if key == "armor":
            return base + TECH["armor"]["per_level"] * t["armor"]
        if key == "speed":
            return base * (1 + TECH["speed"]["per_level"] * t["speed"])
        if key == "vision":
            return base + TECH["vision"]["per_level"] * t["vision"]
        if key == "capacity":
            return int(base * (1 + TECH["capacity"]["per_level"] * t["capacity"]))
        if key == "energy":
            return base * (1 + TECH["energy"]["per_level"] * t["energy"])
        return base

    def structure_armor(self, s):
        return 3 if s.kind == "hq" else STRUCTURES[s.kind]["armor"]

    # ------------------------------------------------------------ scripts
    def set_scripts(self, scripts, assign=None):
        self.scripts = dict(scripts)
        if assign is not None:
            self.assign = dict(assign)
        self.compiled = {}
        self.script_problems = {}
        for name, src in self.scripts.items():
            c = sandbox.CompiledScript(name, src)
            self.compiled[name] = c
            if c.problems:
                self.script_problems[name] = c.problems
        for r in self.robots.values():
            r.ns = None

    def script_for(self, r):
        a = self.assign
        for key in ("robot:%d" % r.id, "group:%s" % r.group if r.group else None, "class:%s" % r.cls,
                    "default"):
            if key and key in a and a[key] in self.compiled:
                return a[key]
        if "main.py" in self.compiled:
            return "main.py"
        return None

    def log(self, text, rid=None, level="info"):
        self.logs.append(dict(tick=self.tick, robot=rid, text=str(text)[:200], level=level))

    # ------------------------------------------------------------ queries
    def in_bounds(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size

    def walkable(self, x, y):
        return self.in_bounds(x, y) and self.grid[y][x] not in defs.BLOCKED_TERRAIN and (x, y) not in self.blocked

    def is_visible(self, team, x, y):
        return bool(self.teams[team].visible[y * self.size + x]) if self.in_bounds(x, y) else False

    def is_explored(self, team, x, y):
        return bool(self.teams[team].explored[y * self.size + x]) if self.in_bounds(x, y) else False

    def structure_at(self, x, y):
        for s in self.structures.values():
            if (x, y) in s.tiles():
                return s
        return None

    def own_hq(self, team):
        for s in self.structures.values():
            if s.team == team and s.kind == "hq":
                return s
        return None

    def dist_to_hq_edge(self, r):
        h = self.own_hq(r.team)
        if h is None:
            return 999
        return max(abs(r.x - h.x) - 1, abs(r.y - h.y) - 1, 0)

    def _update_visibility(self):
        n = self.size
        for t in self.teams.values():
            t.visible = bytearray(n * n)
        for r in self.robots.values():
            if r.alive:
                self._mark(r.team, r.x, r.y, self.stat(r, "vision"))
        for s in self.structures.values():
            if s.built:
                rad = 7 if s.kind == "hq" else (6 if s.kind == "turret" else 3)
                self._mark(s.team, s.x, s.y, rad)
        for t in self.teams.values():
            ex, vi = t.explored, t.visible
            for i in range(n * n):
                if vi[i]:
                    ex[i] = 1

    def _mark(self, team, cx, cy, rad):
        n, vis = self.size, self.teams[team].visible
        ri = int(rad)
        r2 = rad * rad + 0.5
        for y in range(max(0, cy - ri), min(n, cy + ri + 1)):
            dy2 = (y - cy) ** 2
            base = y * n
            for x in range(max(0, cx - ri), min(n, cx + ri + 1)):
                if (x - cx) ** 2 + dy2 <= r2:
                    vis[base + x] = 1

    # ------------------------------------------------------------ pathing
    def robot_path(self, r, goal, ignore_robots=True):
        blocked = set(self.blocked)
        if not ignore_robots:
            blocked |= {p for p, rid in self.occ.items() if rid != r.id}
        return worldgen.find_path(self.grid, blocked, (r.x, r.y), goal)

    # ------------------------------------------------------------ main step
    def step(self, n=1):
        for _ in range(n):
            if self.result is not None:
                break
            self._one_tick()

    def _one_tick(self):
        self.tick += 1
        self.events = []
        for r in self.robots.values():
            r.acted = False
            r.action = "idle"
            r.target = None
            if r.cd > 0:
                r.cd -= 1
        from . import ai, api
        # team commanders then robot scripts
        for tid in list(self.teams):
            if tid == 0:
                self._run_player_scripts(api)
            else:
                ai.run_team(self, tid)
        self._movement()
        self._structures_tick()
        self._production()
        self._update_visibility()
        self._pickups()
        for t in self.teams.values():
            t.stats["peak_robots"] = max(t.stats["peak_robots"], sum(1 for r in self.robots.values() if r.team == t.id))
        for r in self.robots.values():
            if r.team == 0:
                self.teams[0].stats["robot_ticks"] += 1
                if r.action == "idle":
                    self.teams[0].stats["idle_ticks"] += 1
            if r.energy <= 0.01:
                self.teams[r.team].stats["empty_energy_ticks"] += 1
        from . import modes
        modes.evaluate(self)

    def _run_player_scripts(self, api):
        t0 = _now()
        team = self.teams[0]
        if self.compiled:
            cname = self.assign.get("commander")
            if cname and cname in self.compiled:
                self._call_commander(api, cname)
        for r in sorted((x for x in self.robots.values() if x.team == 0), key=lambda x: x.id):
            if _now() - t0 > self.team_time_budget:
                team.stats["budget_overruns"] += 1
                self.log("team time budget exceeded; remaining robots skipped this tick", level="warn")
                break
            sname = self.script_for(r)
            if sname is None:
                continue
            self._call_robot(api, r, sname)

    def _namespace(self, r, sname):
        c = self.compiled[sname]
        key = (sname, id(c))
        if r.ns is not None and r.script_key == key:
            return r.ns
        r.script_key = key
        rid = r.id
        ns = sandbox.make_namespace(lambda m: self._script_print(rid, m), random.Random(self.seed + rid))
        b = sandbox.Budget(self.line_budget, self.robot_time_budget * 3, check_memory=False)
        ok, res = sandbox.exec_module(c, ns, b)
        r.ns = ns if ok else None
        if not ok:
            self._script_error(r, sname, res)
        return r.ns

    def _script_print(self, rid, msg):
        self.log(msg, rid, "print")

    def _script_error(self, r, sname, msg):
        self.teams[r.team].stats["script_errors"] += 1
        r.err_count += 1
        if "BudgetExceeded" in msg:
            self.teams[r.team].stats["budget_overruns"] += 1
        key = (r.id, msg)
        if self.last_logged_error.get(r.id) != msg:
            self.log("%s: %s" % (sname, msg), r.id, "error")
            self.last_logged_error[r.id] = msg
        r.last_error = msg

    def _call_robot(self, api, r, sname):
        c = self.compiled[sname]
        if c.code is None:
            if sname not in self.last_logged_error:
                self.last_logged_error[sname] = True
                self.log("%s has errors: %s" % (sname, c.problems[0]["message"]), r.id, "error")
            return
        ns = self._namespace(r, sname)
        if ns is None:
            return
        fn = ns.get("update")
        if not callable(fn):
            return
        b = sandbox.Budget(self.line_budget, self.robot_time_budget, check_memory=self.memory_check)
        ok, res = sandbox.run_call(c.filename, fn, (api.RobotAPI(self, r),), b)
        if not ok:
            self._script_error(r, sname, res)
        else:
            r.last_error = "" if not r.last_error.startswith("cmd:") else r.last_error
            self.last_logged_error.pop(r.id, None)

    def _call_commander(self, api, cname):
        c = self.compiled[cname]
        if c.code is None:
            return
        ns = self.ai_state.get(("cmdns", cname, id(c)))
        if ns is None:
            ns = sandbox.make_namespace(lambda m: self.log(m, None, "print"), random.Random(self.seed))
            ok, res = sandbox.exec_module(c, ns, sandbox.Budget(self.line_budget, 0.06, check_memory=False))
            if not ok:
                self.log("%s: %s" % (cname, res), None, "error")
                self.teams[0].stats["script_errors"] += 1
                return
            self.ai_state[("cmdns", cname, id(c))] = ns
        fn = ns.get("commander")
        if not callable(fn):
            return
        b = sandbox.Budget(self.line_budget, self.robot_time_budget * 2, check_memory=self.memory_check)
        ok, res = sandbox.run_call(c.filename, fn, (api.BaseAPI(self, 0),), b)
        if not ok:
            self.teams[0].stats["script_errors"] += 1
            if self.last_logged_error.get("cmd") != res:
                self.log("%s: %s" % (cname, res), None, "error")
                self.last_logged_error["cmd"] = res

    # ------------------------------------------------------------ phases
    def _movement(self):
        for r in sorted(self.robots.values(), key=lambda x: x.id):
            if not r.alive or not r.path:
                continue
            speed = self.stat(r, "speed")
            r.mp = min(r.mp + speed, speed * 2 + 1)
            moved = False
            while r.path:
                nx, ny = r.path[0]
                cost = defs.TERRAIN_COST.get(self.grid[ny][nx], 1.0) * (1.4142 if (nx != r.x and ny != r.y) else 1.0)
                if r.mp < cost:
                    break
                if (nx, ny) in self.blocked:
                    r.path = []
                    r.last_error = "path blocked"
                    break
                other = self.occ.get((nx, ny))
                if other is not None and other != r.id:
                    r.blocked_ticks += 1
                    if r.blocked_ticks >= 3 and r.goal:
                        np_ = self.robot_path(r, r.goal, ignore_robots=False)
                        r.path = np_ or []
                        r.blocked_ticks = 0
                    break
                ecost = COSTS["move_per_tile"] * cost
                if r.energy < ecost:
                    self.teams[r.team].stats["empty_energy_ticks"] += 0
                    r.last_error = "out of energy"
                    break
                r.energy -= ecost
                r.mp -= cost
                del self.occ[(r.x, r.y)]
                r.facing = math.atan2(ny - r.y, nx - r.x)
                r.x, r.y = nx, ny
                self.occ[(nx, ny)] = r.id
                r.path.pop(0)
                r.blocked_ticks = 0
                moved = True
            if moved:
                r.action = "move" if r.action == "idle" else r.action
            if not r.path:
                r.goal = None

    def _structures_tick(self):
        # construction
        for r in list(self.robots.values()):
            j = r.job
            if not j:
                continue
            s = self.structures.get(j["sid"])
            if s is None or s.built or not r.alive:
                r.job = None
                continue
            if dist(r.x, r.y, s.x, s.y) > 2.6:
                r.job = None
                continue
            if r.energy < COSTS["build"]:
                continue
            r.energy -= COSTS["build"]
            eff = 1.0 if CLASSES[r.cls]["build"] >= 1 and r.cls == "builder" else 0.6
            s.progress += eff
            r.action = "build"
            r.target = (s.x, s.y)
            bt = STRUCTURES[s.kind]["build_time"]
            s.hp = max(1.0, s.max_hp * min(1.0, s.progress / bt))
            if s.progress >= bt:
                s.built = True
                s.hp = s.max_hp
                r.job = None
                self.teams[r.team].stats["built"] += 1
                self.events.append(dict(t="built", id=s.id, x=s.x, y=s.y, kind=s.kind, team=s.team))
        # turrets and HQ defence, solar recharge
        for s in list(self.structures.values()):
            if not s.built:
                continue
            if s.cd > 0:
                s.cd -= 1
            if s.kind in ("turret", "hq"):
                rng, dmg, cd = (6.0, 9, 2) if s.kind == "turret" else (4.5, 5, 3)
                if s.cd > 0:
                    continue
                dmg *= 1 + TECH["damage"]["per_level"] * self.teams[s.team].tech["damage"]
                best, bd = None, 1e9
                for r in self.robots.values():
                    if r.team != s.team and r.alive:
                        d = dist(r.x, r.y, s.x, s.y)
                        if d <= rng and d < bd:
                            best, bd = r, d
                if best:
                    s.cd = cd
                    s.angle = math.atan2(best.y - s.y, best.x - s.x)
                    self._damage_robot(best, dmg, s.team, src=("structure", s.id))
                    self.events.append(dict(t="attack", fx=s.x, fy=s.y, tx=best.x, ty=best.y, src=s.id,
                                            dst=best.id, kind="turret", team=s.team))
            elif s.kind == "solar":
                for r in self.robots.values():
                    if r.team == s.team and dist(r.x, r.y, s.x, s.y) <= 2.2:
                        r.energy = min(self.stat(r, "energy"), r.energy + defs.SOLAR_RECHARGE)
        hq_done = [s for s in self.structures.values() if s.kind == "hq"]
        for s in hq_done:
            for r in self.robots.values():
                if r.team == s.team and r.alive and max(abs(r.x - s.x), abs(r.y - s.y)) <= 3 and r.energy < self.stat(r, "energy") * 0.0:
                    pass

    def _production(self):
        for tid, team in self.teams.items():
            slots = 1 + sum(1 for s in self.structures.values() if s.team == tid and s.kind == "factory" and s.built)
            active = team.queues[:slots]
            for item in active:
                item[1] -= 1
            for item in list(active):
                if item[1] <= 0:
                    r = self.spawn_robot(tid, item[0])
                    if r is not None:
                        team.queues.remove(item)
                        team.stats["produced"] += 1
                        r.group = item[2] if len(item) > 2 else ""
                    else:
                        item[1] = 0
            if team.research:
                team.research[1] -= 1
                if team.research[1] <= 0:
                    name = team.research[0]
                    team.tech[name] += 1
                    for r in self.robots.values():
                        if r.team == tid and name == "energy":
                            r.energy += TECH["energy"]["per_level"] * CLASSES[r.cls]["energy"]
                    team.research = None
                    self.events.append(dict(t="research", name=name, team=tid))

    def _pickups(self):
        for t in self.teams.values():
            pass
        for b in self.beacons:
            if b["found"]:
                continue
            for r in self.robots.values():
                if r.team == 0 and dist(r.x, r.y, b["x"], b["y"]) <= 1.5:
                    b["found"] = True
                    self.teams[0].stats["beacons"] += 1
                    self.events.append(dict(t="beacon", x=b["x"], y=b["y"]))
                    break
        if self.checkpoints:
            for r in self.robots.values():
                if r.team == 0 and r.checkpoint_idx < len(self.checkpoints):
                    cx, cy = self.checkpoints[r.checkpoint_idx]
                    if dist(r.x, r.y, cx, cy) <= 1.6:
                        r.checkpoint_idx += 1
                        self.teams[0].stats["checkpoints"] = r.checkpoint_idx
                        self.events.append(dict(t="checkpoint", x=cx, y=cy, idx=r.checkpoint_idx))

    # ------------------------------------------------------------ damage
    def _damage_robot(self, r, dmg, from_team, src=None):
        arm = self.stat(r, "armor")
        eff = max(1.0, dmg * 20.0 / (20.0 + arm))
        r.hp -= eff
        self.teams[r.team].stats["damage_taken"] += eff
        self.teams[from_team].stats["damage_dealt"] += eff
        if r.hp <= 0 and r.alive:
            self._kill_robot(r, from_team, src)

    def _damage_structure(self, s, dmg, from_team):
        arm = self.structure_armor(s)
        eff = max(1.0, dmg * 20.0 / (20.0 + arm))
        s.hp -= eff
        self.teams[s.team].stats["damage_taken"] += eff
        self.teams[from_team].stats["damage_dealt"] += eff
        if s.hp <= 0:
            for t in s.tiles():
                self.blocked.discard(t)
            self.structures.pop(s.id, None)
            self.teams[s.team].stats["structures_lost"] += 1
            self.events.append(dict(t="death", id=s.id, x=s.x, y=s.y, kind=s.kind, team=s.team, struct=True))

    def _kill_robot(self, r, from_team, src):
        r.alive = False
        r.action = "dead"
        self.occ.pop((r.x, r.y), None)
        self.robots.pop(r.id, None)
        self.teams[r.team].stats["losses"] += 1
        self.teams[from_team].stats["kills"] += 1
        cause = "turret" if src and src[0] == "structure" else "robot"
        self.teams[r.team].lost_by_cause[(r.cls, cause)] = self.teams[r.team].lost_by_cause.get((r.cls, cause), 0) + 1
        self.events.append(dict(t="death", id=r.id, x=r.x, y=r.y, kind="robot", cls=r.cls, team=r.team))

    # ------------------------------------------------------------ debugger
    def debug_robot(self, rid, breakpoints=()):
        """Run one tick of robot `rid`'s script on a COPY of the game; returns line trace,
        breakpoint snapshots (variable inspection) and the resulting action. Real game untouched."""
        from . import api
        sim = Sim.from_dict(self.to_dict())
        r = sim.robots.get(rid)
        if r is None or r.team != 0:
            return dict(ok=False, error="robot not found", snapshots=[], trace=[], logs=[])
        sname = sim.script_for(r)
        if sname is None or sim.compiled[sname].code is None:
            return dict(ok=False, error="no runnable script assigned", snapshots=[], trace=[], logs=[])
        c = sim.compiled[sname]
        ns = sim._namespace(r, sname)
        fn = ns.get("update") if ns else None
        if not callable(fn):
            return dict(ok=False, error="script defines no update(robot)", snapshots=[], trace=[], logs=[])
        b = sandbox.Budget(sim.line_budget, 1.0, check_memory=False)
        b.breakpoints = {c.filename: set(int(x) for x in breakpoints)}
        b.line_trace = []
        ok, res = sandbox.run_call(c.filename, fn, (api.RobotAPI(sim, r),), b)
        return dict(ok=ok, error=None if ok else res, script=sname, snapshots=b.snapshots, trace=b.line_trace,
                    lines=b.lines, action=r.action, logs=[l["text"] for l in list(sim.logs)[-20:]],
                    memory=_jsonable(r.memory))

    # ------------------------------------------------------------ snapshot
    def snapshot(self, full=False):
        t0 = self.teams[0]
        return dict(
            tick=self.tick, max_ticks=self.max_ticks,
            robots=[dict(id=r.id, team=r.team, cls=r.cls, x=r.x, y=r.y, hp=round(r.hp, 1),
                         maxhp=CLASSES[r.cls]["hp"], energy=round(r.energy, 1),
                         maxenergy=round(self.stat(r, "energy"), 1), cargo=r.cargo, action=r.action,
                         facing=round(r.facing, 2), group=r.group, target=r.target,
                         script=self.script_for(r) if r.team == 0 else None, err=r.last_error[:80],
                         vision=self.stat(r, "vision"))
                    for r in self.robots.values() if r.team == 0 or self.is_visible(0, r.x, r.y)],
            structures=[dict(id=s.id, team=s.team, kind=s.kind, x=s.x, y=s.y, hp=round(s.hp, 1),
                             maxhp=s.max_hp, built=s.built, angle=round(s.angle, 2))
                        for s in self.structures.values() if s.team == 0 or self.is_explored(0, s.x, s.y)],
            ore=[dict(id=o.id, x=o.x, y=o.y, amount=o.amount, max=o.max_amount) for o in self.ores.values()
                 if self.is_explored(0, o.x, o.y)],
            beacons=[b for b in self.beacons if b["found"] or self.is_explored(0, b["x"], b["y"])],
            checkpoints=[list(c) for c in self.checkpoints],
            events=self.events,
            team=dict(credits=t0.credits, alloy=t0.alloy, tech=t0.tech,
                      research=t0.research, queue=[[q[0], q[1]] for q in t0.queues],
                      stats={k: (round(v, 1) if isinstance(v, float) else v) for k, v in t0.stats.items()}),
            enemy=(dict(credits=self.teams[1].credits) if False else None),
            explored=_pack(t0.explored),
            visible=_pack(t0.visible),
            logs=list(self.logs)[-60:],
            objectives=getattr(self, "objective_status", []),
            result=self.result,
        )

    def world_info(self):
        return dict(size=self.size, grid=self.grid, trees=self.trees, world=self.world_id,
                    palette=defs.WORLDS[self.world_id]["palette"], hq=[list(self.hq_pos[t]) for t in self.teams],
                    mode=self.mode)

    # ------------------------------------------------------------ save/load
    def to_dict(self):
        return dict(
            config=self.config, tick=self.tick, next_id=self.next_id, rng=_rng_state(self.rng),
            robots=[dict(id=r.id, team=r.team, cls=r.cls, x=r.x, y=r.y, hp=r.hp, energy=r.energy,
                         cargo=r.cargo, memory=_jsonable(r.memory), group=r.group, mp=r.mp, cd=r.cd,
                         checkpoint_idx=r.checkpoint_idx, goal=r.goal, spawned=r.spawned,
                         path=[list(q) for q in r.path], job=r.job, facing=r.facing,
                         blocked_ticks=r.blocked_ticks, last_error=r.last_error)
                    for r in self.robots.values()],
            structures=[dict(id=s.id, team=s.team, kind=s.kind, x=s.x, y=s.y, hp=s.hp, progress=s.progress,
                             built=s.built) for s in self.structures.values()],
            ores=[dict(id=o.id, x=o.x, y=o.y, amount=o.amount, max=o.max_amount) for o in self.ores.values()],
            beacons=self.beacons, checkpoints=[list(c) for c in self.checkpoints],
            teams={str(t.id): dict(credits=t.credits, alloy=t.alloy, tech=t.tech, research=t.research,
                                   queues=t.queues, explored=_pack(t.explored), stats=t.stats,
                                   memory=_jsonable(t.memory)) for t in self.teams.values()},
            scripts=self.scripts, assign=self.assign, result=self.result,
            ai_mem={str(k[1]): _jsonable(v) for k, v in self.ai_state.items()
                    if isinstance(k, tuple) and k and k[0] == "ai"},
            lost={str(t.id): [[c, cause, n] for (c, cause), n in t.lost_by_cause.items()] for t in self.teams.values()},
        )

    @classmethod
    def from_dict(cls, d):
        sim = cls(d["config"])
        sim.tick, sim.next_id = d["tick"], d["next_id"]
        _set_rng_state(sim.rng, d["rng"])
        sim.robots.clear()
        sim.occ.clear()
        sim.structures.clear()
        sim.blocked.clear()
        sim.ores.clear()
        for s in d["structures"]:
            st = Structure(s["id"], s["team"], s["kind"], s["x"], s["y"])
            st.hp, st.progress, st.built = s["hp"], s["progress"], s["built"]
            sim.structures[st.id] = st
            for t in st.tiles():
                sim.blocked.add(t)
        for o in d["ores"]:
            ore = Ore(o["id"], o["x"], o["y"], o["amount"])
            ore.max_amount = o["max"]
            sim.ores[ore.id] = ore
            if ore.amount > 0:
                sim.blocked.add((ore.x, ore.y))
        for rd in d["robots"]:
            r = Robot(rd["id"], rd["team"], rd["cls"], rd["x"], rd["y"])
            r.hp, r.energy, r.cargo = rd["hp"], rd["energy"], rd["cargo"]
            r.memory, r.group, r.mp, r.cd = rd["memory"], rd["group"], rd["mp"], rd["cd"]
            r.checkpoint_idx = rd.get("checkpoint_idx", 0)
            r.spawned = rd.get("spawned", 0)
            r.path = [tuple(q) for q in rd.get("path", [])]
            r.goal = tuple(rd["goal"]) if rd.get("goal") else None
            r.job = rd.get("job")
            r.facing = rd.get("facing", 0.0)
            r.blocked_ticks = rd.get("blocked_ticks", 0)
            r.last_error = rd.get("last_error", "")
            sim.robots[r.id] = r
            sim.occ[(r.x, r.y)] = r.id
        sim.beacons = d["beacons"]
        sim.checkpoints = [tuple(c) for c in d["checkpoints"]]
        for tid, td in d["teams"].items():
            t = sim.teams[int(tid)]
            t.credits, t.alloy, t.tech = td["credits"], td["alloy"], td["tech"]
            t.research, t.queues, t.stats = td["research"], td["queues"], td["stats"]
            t.memory = td.get("memory", {})
            t.explored = _unpack(td["explored"], sim.size)
        for tid, mem in d.get("ai_mem", {}).items():
            sim.ai_state[("ai", int(tid))] = mem
        for tid, items in d.get("lost", {}).items():
            sim.teams[int(tid)].lost_by_cause = {(c, cause): n for c, cause, n in items}
        sim.set_scripts(d["scripts"], d["assign"])
        sim.result = d.get("result")
        sim._update_visibility()
        return sim


def _now():
    import time
    return time.perf_counter()


def _pack(ba):
    import base64
    n = len(ba)
    bits = bytearray((n + 7) // 8)
    for i in range(n):
        if ba[i]:
            bits[i >> 3] |= 1 << (i & 7)
    return base64.b64encode(bytes(bits)).decode("ascii")


def _unpack(s, size):
    import base64
    bits = base64.b64decode(s)
    out = bytearray(size * size)
    for i in range(size * size):
        if bits[i >> 3] & (1 << (i & 7)):
            out[i] = 1
    return out


def _rng_state(rng):
    v = rng.getstate()
    return [v[0], list(v[1]), v[2]]


def _set_rng_state(rng, st):
    rng.setstate((st[0], tuple(st[1]), st[2]))


def _jsonable(o, depth=0):
    if depth > 6:
        return None
    if isinstance(o, dict):
        return {str(k): _jsonable(v, depth + 1) for k, v in list(o.items())[:200]}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v, depth + 1) for v in list(o)[:500]]
    if isinstance(o, (int, float, str, bool)) or o is None:
        return o
    return str(o)
