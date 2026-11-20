"""JSON bridge called from Kotlin (Chaquopy). Every function takes/returns JSON strings (or primitives)
so the Dart/Kotlin side never touches Python objects. One active game session at a time."""
import json

from . import ENGINE_VERSION, analysis, api_spec, defs, lessons, modes, puzzles, sandbox, sim as simmod, templates, worldgen

_game = None


def _j(o):
    return json.dumps(o, separators=(",", ":"))


def version():
    import sys
    return _j(dict(engine=ENGINE_VERSION, python=sys.version.split()[0]))


def catalog():
    return _j(dict(
        classes={k: dict(v) for k, v in defs.CLASSES.items()},
        structures=defs.STRUCTURES, tech=defs.TECH, costs=defs.COSTS,
        difficulties=defs.DIFFICULTY, worlds={k: dict(name=v["name"], blurb=v["blurb"], palette=v["palette"])
                                              for k, v in defs.WORLDS.items()},
        modes=modes.MODES, templates=templates.get_templates(), starter_assign=templates.STARTER_ASSIGN,
        limits=dict(allowed_modules=sorted(sandbox.ALLOWED_MODULES), forbidden_names=sorted(sandbox.FORBIDDEN_NAMES),
                    max_pow_exp=sandbox.MAX_POW_EXP, max_seq=sandbox.MAX_SEQ),
        max_pop=simmod.MAX_POP,
    ))


def api_reference():
    return _j(api_spec.get_spec())


def puzzle_list():
    return _j(puzzles.get_puzzles())


def run_puzzle(pid, source):
    return _j(puzzles.run_puzzle(pid, source))


def check_function(source, func, tests_json):
    tests = [(tuple(t[0]), t[1]) for t in json.loads(tests_json)]
    return _j(puzzles.check_function(source, func, tests))


def validate(source, name="script.py"):
    return _j(sandbox.validate_source(source, name))


def new_game(config_json, scripts_json, assign_json):
    global _game
    cfg = json.loads(config_json)
    mode = cfg.pop("mode", "robot_wars")
    full = modes.build_config(mode, cfg.pop("difficulty", "normal"), cfg.pop("world", "ironvale"),
                              int(cfg.pop("seed", 1)), bool(cfg.pop("advanced_mode", False)), cfg or None)
    _game = simmod.Sim(full)
    _game.set_scripts(json.loads(scripts_json), json.loads(assign_json))
    return _j(dict(world=_game.world_info(), snapshot=_game.snapshot(full=True),
                   problems=_game.script_problems))


def set_scripts(scripts_json, assign_json):
    _need()
    _game.set_scripts(json.loads(scripts_json), json.loads(assign_json))
    return _j(_game.script_problems)


def step(n=1):
    _need()
    _game.step(int(n))
    return _j(_game.snapshot())


def snapshot(full=False):
    _need()
    return _j(_game.snapshot(full=bool(full)))


def _need():
    if _game is None:
        raise RuntimeError("no game running")


def build_robot(cls):
    _need()
    from .api import BaseAPI
    try:
        return _j(bool(BaseAPI(_game, 0).build_robot(cls)))
    except ValueError:
        return _j(False)


def research(name):
    _need()
    from .api import BaseAPI
    try:
        return _j(bool(BaseAPI(_game, 0).research(name)))
    except ValueError:
        return _j(False)


def set_group(rid, group):
    _need()
    r = _game.robots.get(int(rid))
    if r is None or r.team != 0:
        return _j(False)
    r.group = str(group)[:20]
    return _j(True)


def assign(key, script):
    _need()
    if script in (None, "", "none"):
        _game.assign.pop(key, None)
        return _j(True)
    if script not in _game.compiled:
        return _j(False)
    _game.assign[key] = script
    return _j(True)


def robot_info(rid):
    _need()
    r = _game.robots.get(int(rid))
    if r is None:
        return _j(None)
    spec = defs.CLASSES[r.cls]
    caps = [c for c, key in (("attack", "damage"), ("mine", "mine"), ("build", "build"), ("repair", "repair"))
            if spec[key] > 0]
    methods = [s["name"] for s in api_spec.get_spec() if s["owner"] == "robot" and s["kind"] == "method"]
    gated = {"attack": "attack", "mine": "mine", "build": "build", "repair": "repair", "share_energy": "share_energy"}
    avail = [m for m in methods if m not in gated or r.cls in api_spec.CLASS_NOTES.get(gated[m], [])]
    return _j(dict(id=r.id, cls=r.cls, team=r.team, x=r.x, y=r.y, hp=round(r.hp, 1), energy=round(r.energy, 1),
                   cargo=r.cargo, group=r.group, script=_game.script_for(r) if r.team == 0 else None,
                   error=r.last_error, history=list(r.history)[-20:], memory=simmod._jsonable(r.memory),
                   stats=dict(damage=round(_game.stat(r, "damage"), 1), armor=_game.stat(r, "armor"),
                              speed=round(_game.stat(r, "speed"), 2), vision=_game.stat(r, "vision"),
                              capacity=_game.stat(r, "capacity"), range=spec["range"]),
                   abilities=caps, api=avail, desc=spec["desc"]))


def debug_robot(rid, breakpoints_json):
    _need()
    return _j(_game.debug_robot(int(rid), json.loads(breakpoints_json)))


def analysis_report():
    _need()
    return _j(analysis.analyze(_game))


def save_game():
    _need()
    return _j(_game.to_dict())


def load_game(blob):
    global _game
    _game = simmod.Sim.from_dict(json.loads(blob))
    return _j(dict(world=_game.world_info(), snapshot=_game.snapshot(full=True), problems=_game.script_problems))


def lesson_list():
    return _j(lessons.get_lessons())


def run_lesson(lid, source):
    return _j(lessons.run_lesson(lid, source))


def campaign():
    return _j(modes.CAMPAIGN)


def campaign_config(mid):
    return _j(modes.campaign_config(mid))


def world_preview(world, size, seed):
    w = worldgen.generate_world(world, int(size), int(seed))
    return _j(dict(grid=w["grid"], hq=[list(h) for h in w["hq"]], ore=[[o["x"], o["y"]] for o in w["ore"]]))


def start_campaign(mid, scripts_json, assign_json, advanced=False):
    """Start a campaign mission using its fixed configuration."""
    global _game
    cfg = modes.campaign_config(mid, bool(advanced))
    _game = simmod.Sim(cfg)
    _game.set_scripts(json.loads(scripts_json), json.loads(assign_json))
    return _j(dict(world=_game.world_info(), snapshot=_game.snapshot(full=True), problems=_game.script_problems))


def mission_objectives(mode, difficulty):
    cfg = modes.build_config(mode, difficulty, "ironvale", 1)
    return _j([o.get("title", o["type"]) for o in cfg.get("objectives", [])])
