"""Player-facing API objects handed to scripts (`robot` and `base`).

Every public attribute/method here must have an entry in api_spec.py (enforced by tests).
Commands return True/False; on failure they set robot.last_error to 'cmd: <reason>'.
Type misuse raises TypeError so it shows up in the editor log with a line number.
"""
import math

from . import defs
from .defs import CLASSES, COSTS, STRUCTURES, TECH


class View:
    """Read-only snapshot of something a robot can see."""
    __slots__ = ("id", "kind", "cls", "team", "x", "y", "health", "max_health", "amount", "distance",
                 "ally", "built", "energy", "cargo", "group")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    @property
    def pos(self):
        return (self.x, self.y)

    def dist_to(self, x, y):
        return round(math.hypot(self.x - x, self.y - y), 2)

    def __repr__(self):
        return "<%s %s#%s at (%s,%s)%s>" % (
            "ally" if self.ally else "enemy" if self.ally is False else "neutral", self.cls or self.kind,
            self.id, self.x, self.y, "" if self.health is None else " hp=%d" % self.health)


def _num(v, name):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError("%s must be a number, got %s" % (name, type(v).__name__))
    return v


def _rview(sim, r, me=None):
    d = round(math.hypot(r.x - me.x, r.y - me.y), 2) if me else None
    return View(id=r.id, kind="robot", cls=r.cls, team=r.team, x=r.x, y=r.y, health=round(r.hp, 1),
                max_health=CLASSES[r.cls]["hp"], distance=d, ally=(me.team == r.team) if me else None)


def _sview(s, me=None):
    d = round(math.hypot(s.x - me.x, s.y - me.y), 2) if me else None
    return View(id=s.id, kind=s.kind if s.kind == "hq" else "structure", cls=s.kind, team=s.team, x=s.x, y=s.y,
                health=round(s.hp, 1), max_health=s.max_hp, distance=d,
                ally=(me.team == s.team) if me else None, built=s.built)


def _oview(o, me=None):
    d = round(math.hypot(o.x - me.x, o.y - me.y), 2) if me else None
    return View(id=o.id, kind="resource", cls="ore", team=None, x=o.x, y=o.y, amount=o.amount, distance=d)


class RobotAPI:
    __slots__ = ("_s", "_r")

    def __init__(self, sim, robot):
        self._s = sim
        self._r = robot

    def __repr__(self):
        return "<robot %s#%d at (%d,%d)>" % (self._r.cls, self._r.id, self._r.x, self._r.y)

    # ---------------------------------------------------------- properties
    @property
    def id(self): return self._r.id
    @property
    def cls(self): return self._r.cls
    @property
    def team(self): return self._r.team
    @property
    def x(self): return self._r.x
    @property
    def y(self): return self._r.y
    @property
    def pos(self): return (self._r.x, self._r.y)
    @property
    def health(self): return round(self._r.hp, 1)
    @property
    def max_health(self): return CLASSES[self._r.cls]["hp"]
    @property
    def energy(self): return round(self._r.energy, 1)
    @property
    def max_energy(self): return round(self._s.stat(self._r, "energy"), 1)
    @property
    def cargo(self): return self._r.cargo
    @property
    def capacity(self): return self._s.stat(self._r, "capacity")
    @property
    def tick(self): return self._s.tick
    @property
    def group(self): return self._r.group
    @property
    def memory(self): return self._r.memory
    @property
    def team_memory(self): return self._s.teams[self._r.team].memory
    @property
    def hq(self):
        h = self._s.own_hq(self._r.team)
        return (h.x, h.y) if h else None
    @property
    def enemy_hq(self):
        t = 1 - self._r.team
        return tuple(self._s.hq_pos[t]) if t in self._s.teams else None
    @property
    def vision(self): return self._s.stat(self._r, "vision")
    @property
    def speed(self): return round(self._s.stat(self._r, "speed"), 2)
    @property
    def attack_range(self): return CLASSES[self._r.cls]["range"]
    @property
    def damage(self): return round(self._s.stat(self._r, "damage"), 1)
    @property
    def armor(self): return self._s.stat(self._r, "armor")
    @property
    def ready(self): return self._r.cd <= 0 and not self._r.acted
    @property
    def moving(self): return bool(self._r.path)
    @property
    def last_error(self): return self._r.last_error
    @property
    def checkpoint(self):
        s = self._s
        i = self._r.checkpoint_idx
        return tuple(s.checkpoints[i]) if i < len(s.checkpoints) else None
    @property
    def team_credits(self): return self._s.teams[self._r.team].credits

    # ---------------------------------------------------------- helpers
    def _fail(self, why):
        self._r.last_error = "cmd: " + why
        return False

    def _hist(self, what):
        self._r.history.append((self._s.tick, what))

    def _act(self, label, energy, target=None):
        r = self._r
        if r.acted:
            return self._fail("already acted this tick")
        if r.energy < energy:
            return self._fail("not enough energy (need %.1f)" % energy)
        r.acted = True
        r.energy -= energy
        r.action = label
        r.target = target
        self._hist(label)
        return True

    def _find(self, target):
        s = self._s
        if hasattr(target, "id") and hasattr(target, "kind"):
            tid = target.id
        else:
            raise TypeError("target must be an object returned by scan()/enemies()/resources()")
        if tid in s.robots:
            return s.robots[tid]
        if tid in s.structures:
            return s.structures[tid]
        if tid in s.ores:
            return s.ores[tid]
        return None

    # ---------------------------------------------------------- sensing
    def scan(self):
        s, me = self._s, self._r
        vis = self.vision
        out = []
        for r in s.robots.values():
            if r.id != me.id and math.hypot(r.x - me.x, r.y - me.y) <= vis:
                out.append(_rview(s, r, me))
        for st in s.structures.values():
            if math.hypot(st.x - me.x, st.y - me.y) <= vis + (1 if st.kind == "hq" else 0):
                out.append(_sview(st, me))
        for o in s.ores.values():
            if o.amount > 0 and math.hypot(o.x - me.x, o.y - me.y) <= vis:
                out.append(_oview(o, me))
        out.sort(key=lambda v: (v.distance, v.id))
        return out[:80]

    def enemies(self):
        return [v for v in self.scan() if v.ally is False]

    def allies(self):
        return [v for v in self.scan() if v.ally is True and v.kind == "robot"]

    def structures(self):
        return [v for v in self.scan() if v.kind in ("structure", "hq")]

    def resources(self):
        return [v for v in self.scan() if v.kind == "resource"]

    def nearest_enemy(self):
        e = self.enemies()
        return e[0] if e else None

    def enemy_visible(self):
        return bool(self.enemies())

    def nearest_resource(self):
        r = self.resources()
        return r[0] if r else None

    def team_enemies(self):
        s, me = self._s, self._r
        out = [_rview(s, r, me) for r in s.robots.values()
               if r.team != me.team and s.is_visible(me.team, r.x, r.y)]
        out += [_sview(st, me) for st in s.structures.values()
                if st.team != me.team and s.is_visible(me.team, st.x, st.y)]
        out.sort(key=lambda v: (v.distance, v.id))
        return out[:80]

    def known_resources(self):
        s, me = self._s, self._r
        out = [_oview(o, me) for o in s.ores.values() if o.amount > 0 and s.is_explored(me.team, o.x, o.y)]
        out.sort(key=lambda v: (v.distance, v.id))
        return out

    def beacons(self):
        s, me = self._s, self._r
        return [dict(x=b["x"], y=b["y"], found=b["found"]) for b in s.beacons
                if b["found"] or s.is_explored(me.team, b["x"], b["y"])]

    def distance_to(self, x, y):
        return round(math.hypot(_num(x, "x") - self._r.x, _num(y, "y") - self._r.y), 2)

    def can_walk(self, x, y):
        return self._s.walkable(int(_num(x, "x")), int(_num(y, "y")))

    def terrain(self, x, y):
        s = self._s
        x, y = int(_num(x, "x")), int(_num(y, "y"))
        if not s.in_bounds(x, y) or not s.is_explored(self._r.team, x, y):
            return "unknown"
        return ("grass", "sand", "rock", "water")[s.grid[y][x]]

    def at_hq(self):
        return self._s.dist_to_hq_edge(self._r) <= 2

    # ---------------------------------------------------------- movement
    def move_to(self, x, y):
        s, r = self._s, self._r
        x, y = int(_num(x, "x")), int(_num(y, "y"))
        if not s.in_bounds(x, y):
            return self._fail("target outside map")
        if (x, y) == (r.x, r.y):
            r.path, r.goal = [], None
            return True
        if r.goal == (x, y) and r.path:
            return True
        if not s.walkable(x, y):
            return self._fail("target tile (%d,%d) is blocked" % (x, y))
        path = s.robot_path(r, (x, y))
        if path is None:
            return self._fail("no path to (%d,%d)" % (x, y))
        r.path, r.goal = path, (x, y)
        r.blocked_ticks = 0
        r.job = None
        self._hist("move_to(%d,%d)" % (x, y))
        return True

    def approach(self, target, distance=1):
        """Move until within `distance` tiles (Chebyshev) of target."""
        s, r = self._s, self._r
        t = self._find(target)
        if t is None:
            return self._fail("target no longer exists")
        d = max(1, int(_num(distance, "distance")))
        if max(abs(t.x - r.x), abs(t.y - r.y)) <= d:
            r.path, r.goal = [], None
            return True
        if r.goal is not None and r.path and max(abs(r.goal[0] - t.x), abs(r.goal[1] - t.y)) <= d:
            return True
        best, bd = None, 1e9
        for dy in range(-d, d + 1):
            for dx in range(-d, d + 1):
                px, py = t.x + dx, t.y + dy
                if s.walkable(px, py) and ((px, py) not in s.occ or s.occ[(px, py)] == r.id):
                    dd = math.hypot(px - r.x, py - r.y)
                    if dd < bd:
                        best, bd = (px, py), dd
        if best is None:
            return self._fail("no free tile near target")
        return self.move_to(best[0], best[1])

    def stop(self):
        self._r.path, self._r.goal, self._r.job = [], None, None
        return True

    def retreat(self):
        h = self.hq
        if h is None:
            return self._fail("no HQ")
        hq = self._s.own_hq(self._r.team)
        tx, ty = h
        r = self._r
        best, bd = None, 1e9
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                px, py = tx + dx, ty + dy
                if max(abs(dx), abs(dy)) in (2, 3) and self._s.walkable(px, py) and \
                        ((px, py) not in self._s.occ or self._s.occ[(px, py)] == r.id):
                    dd = math.hypot(px - r.x, py - r.y)
                    if dd < bd:
                        best, bd = (px, py), dd
        if best is None:
            return self._fail("no free tile near HQ")
        return self.move_to(*best)

    # ---------------------------------------------------------- actions
    def attack(self, target):
        s, r = self._s, self._r
        spec = CLASSES[r.cls]
        if spec["damage"] <= 0:
            return self._fail("%s has no weapon" % r.cls)
        t = self._find(target)
        if t is None:
            return self._fail("target no longer exists")
        if getattr(t, "team", None) is None or t.team == r.team:
            return self._fail("target is not an enemy")
        if not s.is_visible(r.team, t.x, t.y):
            return self._fail("target not visible")
        d = math.hypot(t.x - r.x, t.y - r.y)
        if d > spec["range"] + (1.0 if hasattr(t, "kind") and t.kind == "hq" else 0):
            return self._fail("target out of range (%.1f > %.1f)" % (d, spec["range"]))
        if r.cd > 0:
            return self._fail("weapon cooling down")
        if not self._act("attack", COSTS["attack"], (t.x, t.y)):
            return False
        r.cd = spec["cooldown"]
        r.facing = math.atan2(t.y - r.y, t.x - r.x)
        s.events.append(dict(t="attack", fx=r.x, fy=r.y, tx=t.x, ty=t.y, src=r.id, dst=t.id,
                             kind=r.cls, team=r.team))
        dmg = s.stat(r, "damage")
        if hasattr(t, "kind"):
            s._damage_structure(t, dmg, r.team)
        else:
            s._damage_robot(t, dmg, r.team, src=("robot", r.id))
        return True

    def mine(self, node):
        s, r = self._s, self._r
        spec = CLASSES[r.cls]
        if spec["mine"] <= 0:
            return self._fail("%s cannot mine" % r.cls)
        o = self._find(node)
        if o is None or o.id not in s.ores:
            return self._fail("resource no longer exists")
        if max(abs(o.x - r.x), abs(o.y - r.y)) > 1:
            return self._fail("must be adjacent to the ore node")
        cap = s.stat(r, "capacity")
        if r.cargo >= cap:
            return self._fail("cargo is full")
        if not self._act("mine", COSTS["mine"], (o.x, o.y)):
            return False
        amt = int(min(spec["mine"], o.amount, cap - r.cargo))
        o.amount -= amt
        r.cargo += amt
        s.teams[r.team].stats["ore_mined"] += amt
        s.events.append(dict(t="mine", id=r.id, x=o.x, y=o.y))
        if o.amount <= 0:
            s.blocked.discard((o.x, o.y))
            s.ores.pop(o.id, None)
        return True

    def deposit(self):
        s, r = self._s, self._r
        if r.cargo <= 0:
            return self._fail("cargo is empty")
        near_ref = None
        for st in s.structures.values():
            if st.team == r.team and st.kind == "refinery" and st.built and \
                    max(abs(st.x - r.x), abs(st.y - r.y)) <= 1:
                near_ref = st
                break
        if near_ref is None and s.dist_to_hq_edge(r) > 2:
            return self._fail("must be next to your HQ or a refinery")
        if not self._act("deposit", 0.0):
            return False
        amt = r.cargo
        r.cargo = 0
        t = s.teams[r.team]
        if near_ref:
            made = amt // 2
            t.alloy += made
            t.stats["alloy_made"] += made
        else:
            t.credits += amt * defs.ORE_PER_CREDIT
        t.stats["ore_delivered"] += amt
        s.events.append(dict(t="deposit", id=r.id, x=r.x, y=r.y))
        return True

    def recharge(self):
        s, r = self._s, self._r
        near = s.dist_to_hq_edge(r) <= 2
        if not near:
            for st in s.structures.values():
                if st.team == r.team and st.kind == "solar" and st.built and \
                        math.hypot(st.x - r.x, st.y - r.y) <= 2.2:
                    near = True
                    break
        if not near:
            return self._fail("must be near your HQ or a solar panel")
        mx = s.stat(r, "energy")
        if r.energy >= mx - 0.01:
            return self._fail("energy already full")
        if not self._act("recharge", 0.0):
            return False
        r.energy = min(mx, r.energy + defs.HQ_RECHARGE * 3)
        return True

    def repair(self, target):
        s, r = self._s, self._r
        spec = CLASSES[r.cls]
        if spec["repair"] <= 0:
            return self._fail("%s cannot repair" % r.cls)
        t = self._find(target)
        if t is None or getattr(t, "team", None) != r.team:
            return self._fail("can only repair friendly robots/structures")
        if math.hypot(t.x - r.x, t.y - r.y) > 2.2:
            return self._fail("target too far (max 2 tiles)")
        mx = t.max_hp if hasattr(t, "kind") else CLASSES[t.cls]["hp"]
        if t.hp >= mx - 0.01:
            return self._fail("target already at full health")
        if not self._act("repair", COSTS["repair"], (t.x, t.y)):
            return False
        before = t.hp
        t.hp = min(mx, t.hp + spec["repair"])
        s.teams[r.team].stats["repaired"] += t.hp - before
        s.events.append(dict(t="repair", x=t.x, y=t.y))
        return True

    def share_energy(self, target, amount):
        s, r = self._s, self._r
        amount = _num(amount, "amount")
        t = self._find(target)
        if t is None or not hasattr(t, "energy") or t.team != r.team:
            return self._fail("can only share energy with friendly robots")
        if math.hypot(t.x - r.x, t.y - r.y) > 2.2:
            return self._fail("target too far (max 2 tiles)")
        if r.cls not in ("support", "advanced"):
            return self._fail("only support/advanced robots can share energy")
        amount = max(0.0, min(amount, 20.0, r.energy - 5.0, s.stat(t, "energy") - t.energy))
        if amount <= 0 or not self._act("share", 0.0, (t.x, t.y)):
            return False
        r.energy -= amount
        t.energy += amount
        return True

    def build(self, kind, x, y):
        s, r = self._s, self._r
        if CLASSES[r.cls]["build"] <= 0:
            return self._fail("%s cannot build" % r.cls)
        x, y = int(_num(x, "x")), int(_num(y, "y"))
        # continue an existing job on the same tile
        if r.job:
            st = s.structures.get(r.job["sid"])
            if st and (st.x, st.y) == (x, y) and st.kind == kind and not st.built:
                return True
        if kind not in STRUCTURES:
            return self._fail("unknown structure '%s'" % kind)
        spec = STRUCTURES[kind]
        if math.hypot(x - r.x, y - r.y) > 2.6:
            return self._fail("too far from build site (max 2 tiles)")
        if not s.walkable(x, y) or (x, y) in s.occ:
            return self._fail("build tile is blocked or occupied")
        hq = s.own_hq(r.team)
        if hq and math.hypot(x - hq.x, y - hq.y) > 16:
            return self._fail("build site too far from HQ (max 16 tiles)")
        t = s.teams[r.team]
        if t.credits < spec["cost"]:
            return self._fail("not enough credits (need %d)" % spec["cost"])
        if not self._act("build", COSTS["build"], (x, y)):
            return False
        t.credits -= spec["cost"]
        t.stats["credits_spent"] += spec["cost"]
        st = s._add_structure(r.team, kind, x, y)
        r.job = dict(sid=st.id)
        r.path, r.goal = [], None
        return True

    # ---------------------------------------------------------- misc
    def set_group(self, name):
        if not isinstance(name, str):
            raise TypeError("group name must be a string")
        self._r.group = name[:20]
        return True

    def log(self, text):
        self._s.log(text, self._r.id, "print")

    def history(self):
        return list(self._r.history)


class BaseAPI:
    __slots__ = ("_s", "_t")

    def __init__(self, sim, team):
        self._s = sim
        self._t = team

    def __repr__(self):
        return "<base team %d>" % self._t

    @property
    def credits(self): return self._s.teams[self._t].credits
    @property
    def alloy(self): return self._s.teams[self._t].alloy
    @property
    def tick(self): return self._s.tick
    @property
    def memory(self): return self._s.teams[self._t].memory
    @property
    def hq(self):
        h = self._s.own_hq(self._t)
        return (h.x, h.y) if h else None
    @property
    def enemy_hq(self):
        o = 1 - self._t
        return tuple(self._s.hq_pos[o]) if o in self._s.teams else None
    @property
    def population(self): return sum(1 for r in self._s.robots.values() if r.team == self._t)
    @property
    def queue(self): return [q[0] for q in self._s.teams[self._t].queues]
    @property
    def tech(self): return dict(self._s.teams[self._t].tech)
    @property
    def researching(self):
        r = self._s.teams[self._t].research
        return r[0] if r else None

    def robots(self, cls=None):
        out = []
        for r in sorted(self._s.robots.values(), key=lambda x: x.id):
            if r.team == self._t and (cls is None or r.cls == cls):
                out.append(View(id=r.id, kind="robot", cls=r.cls, team=r.team, x=r.x, y=r.y, health=round(r.hp, 1),
                                max_health=CLASSES[r.cls]["hp"], ally=True,
                                energy=round(r.energy, 1), cargo=r.cargo, group=r.group, distance=0))
        return out

    def my_structures(self):
        return [_sview(s) for s in self._s.structures.values() if s.team == self._t]

    def count(self, cls):
        return sum(1 for r in self._s.robots.values() if r.team == self._t and r.cls == cls)

    def can_afford(self, what):
        c = CLASSES.get(what) or STRUCTURES.get(what)
        return bool(c) and self.credits >= c["cost"]

    def build_robot(self, cls):
        s, t = self._s, self._s.teams[self._t]
        if cls not in CLASSES:
            raise ValueError("unknown robot class '%s'" % cls)
        if self.population + len(t.queues) >= 40:
            return False
        if len(t.queues) >= 6:
            return False
        cost = CLASSES[cls]["cost"]
        if t.credits < cost:
            return False
        t.credits -= cost
        t.stats["credits_spent"] += cost
        t.queues.append([cls, CLASSES[cls]["build_time"], ""])
        return True

    def research(self, name):
        t = self._s.teams[self._t]
        if name not in TECH:
            raise ValueError("unknown tech '%s'" % name)
        lvl = t.tech[name]
        if t.research is not None or lvl >= TECH[name]["levels"]:
            return False
        cost = TECH[name]["costs"][lvl]
        if t.credits < cost:
            return False
        t.credits -= cost
        t.stats["credits_spent"] += cost
        t.research = [name, defs.RESEARCH_TICKS]
        return True

    def set_group(self, robot_id, group):
        r = self._s.robots.get(robot_id)
        if r is None or r.team != self._t:
            return False
        r.group = str(group)[:20]
        return True

    def assign_script(self, key, script_name):
        """key: 'class:miner', 'group:alpha' or 'robot:12'."""
        if not isinstance(key, str) or not (key.startswith(("class:", "group:", "robot:")) or key == "default"):
            raise ValueError("key must look like 'class:miner', 'group:alpha' or 'robot:12'")
        if script_name not in self._s.compiled:
            return False
        self._s.assign[key] = script_name
        return True

    def log(self, text):
        self._s.log(text, None, "print")
