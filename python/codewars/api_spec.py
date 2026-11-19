"""Machine-readable API reference. Single source of truth for the in-game docs, autocomplete and
contextual help; tests assert it matches the real classes and that every example runs."""

# (owner, name, kind, signature, description, params, returns, cost, errors, example_body)
# params: list of (name, type, valid range / notes); example_body is the body of update(robot)
# (owner 'base': body of commander(base)).
_R, _B, _E = "robot", "base", "entity"
_SPEC = [
 # ---------------- robot properties
 (_R, "id", "property", "robot.id", "Unique integer id of this robot.", [], "int", "free", [], "robot.log(robot.id)"),
 (_R, "cls", "property", "robot.cls", "Robot class: scout, miner, builder, defender, support, transport, advanced.", [], "str", "free", [], "if robot.cls == 'miner':\n    robot.log('I mine')"),
 (_R, "team", "property", "robot.team", "Your team number (0 = player).", [], "int", "free", [], "robot.log(robot.team)"),
 (_R, "x", "property", "robot.x", "Current tile column (0 = west edge).", [], "int", "free", [], "robot.log(robot.x)"),
 (_R, "y", "property", "robot.y", "Current tile row (0 = north edge).", [], "int", "free", [], "robot.log(robot.y)"),
 (_R, "pos", "property", "robot.pos", "Current tile as an (x, y) tuple.", [], "tuple[int, int]", "free", [], "x, y = robot.pos\nrobot.log(x + y)"),
 (_R, "health", "property", "robot.health", "Current hit points. At 0 the robot is destroyed.", [], "float", "free", [], "if robot.health < 30:\n    robot.retreat()"),
 (_R, "max_health", "property", "robot.max_health", "Maximum hit points for this class.", [], "int", "free", [], "ratio = robot.health / robot.max_health\nrobot.log(ratio)"),
 (_R, "energy", "property", "robot.energy", "Current energy. Moving and acting costs energy; at 0 the robot is stuck.", [], "float", "free", [], "if robot.energy < 25:\n    robot.retreat()"),
 (_R, "max_energy", "property", "robot.max_energy", "Energy capacity (grows with the energy tech).", [], "float", "free", [], "robot.log(robot.max_energy)"),
 (_R, "cargo", "property", "robot.cargo", "Ore currently carried.", [], "int", "free", [], "if robot.cargo > 0:\n    robot.retreat()"),
 (_R, "capacity", "property", "robot.capacity", "Maximum ore the robot can carry (0 for non-haulers).", [], "int", "free", [], "robot.log(robot.capacity)"),
 (_R, "tick", "property", "robot.tick", "Current simulation tick (4 ticks = 1 second of game time).", [], "int", "free", [], "if robot.tick % 20 == 0:\n    robot.log('twenty ticks')"),
 (_R, "group", "property", "robot.group", "Group label ('' if none). Scripts can be assigned per group.", [], "str", "free", [], "robot.set_group('alpha')\nrobot.log(robot.group)"),
 (_R, "memory", "property", "robot.memory", "A dict that persists between ticks (and across save/load). Keep per-robot state here.", [], "dict", "free", ["Total size is limited; keep values small and JSON-like."], "robot.memory['visits'] = robot.memory.get('visits', 0) + 1"),
 (_R, "team_memory", "property", "robot.team_memory", "A dict shared by every robot on your team: use it to coordinate.", [], "dict", "free", [], "robot.team_memory['last_seen'] = robot.pos"),
 (_R, "hq", "property", "robot.hq", "Your HQ centre as (x, y). The HQ occupies a 3x3 block.", [], "tuple[int, int]", "free", [], "hx, hy = robot.hq\nrobot.move_to(hx + 3, hy)"),
 (_R, "enemy_hq", "property", "robot.enemy_hq", "Enemy HQ centre, or None when there is no enemy. HQ positions are public.", [], "tuple or None", "free", [], "if robot.enemy_hq:\n    robot.log(robot.enemy_hq)"),
 (_R, "vision", "property", "robot.vision", "Sight radius in tiles (grows with vision tech).", [], "float", "free", [], "robot.log(robot.vision)"),
 (_R, "speed", "property", "robot.speed", "Movement points per tick. A grass tile costs 1, sand 2, diagonals x1.41.", [], "float", "free", [], "robot.log(robot.speed)"),
 (_R, "attack_range", "property", "robot.attack_range", "Weapon range in tiles (0 for unarmed classes).", [], "float", "free", [], "robot.log(robot.attack_range)"),
 (_R, "damage", "property", "robot.damage", "Damage per shot before the target's armor (0 if unarmed).", [], "float", "free", [], "robot.log(robot.damage)"),
 (_R, "armor", "property", "robot.armor", "Armor: damage taken is multiplied by 20 / (20 + armor), minimum 1.", [], "float", "free", [], "robot.log(robot.armor)"),
 (_R, "ready", "property", "robot.ready", "True if the weapon is cooled down and no action was used this tick.", [], "bool", "free", [], "if robot.ready:\n    robot.log('ready')"),
 (_R, "moving", "property", "robot.moving", "True while following a path.", [], "bool", "free", [], "if not robot.moving:\n    robot.move_to(robot.x + 1, robot.y)"),
 (_R, "last_error", "property", "robot.last_error", "Reason the most recent command failed, e.g. 'cmd: target out of range'.", [], "str", "free", [], "if robot.last_error:\n    robot.log(robot.last_error)"),
 (_R, "checkpoint", "property", "robot.checkpoint", "Next racing checkpoint as (x, y), or None outside Racing / when finished.", [], "tuple or None", "free", [], "cp = robot.checkpoint\nif cp:\n    robot.move_to(cp[0], cp[1])"),
 (_R, "team_credits", "property", "robot.team_credits", "Credits your team currently holds.", [], "int", "free", [], "robot.log(robot.team_credits)"),
 # ---------------- robot sensing
 (_R, "scan", "method", "robot.scan()", "Everything within vision: robots, structures, HQs and ore nodes, nearest first (max 80).", [], "list[Entity]", "free", [], "for e in robot.scan():\n    robot.log(e)"),
 (_R, "enemies", "method", "robot.enemies()", "Visible enemy robots and structures within your own vision, nearest first.", [], "list[Entity]", "free", [], "for e in robot.enemies():\n    robot.log(e.distance)"),
 (_R, "allies", "method", "robot.allies()", "Friendly robots within your vision.", [], "list[Entity]", "free", [], "hurt = [a for a in robot.allies() if a.health < a.max_health]\nrobot.log(len(hurt))"),
 (_R, "structures", "method", "robot.structures()", "Structures and HQs (both teams) within your vision.", [], "list[Entity]", "free", [], "robot.log(len(robot.structures()))"),
 (_R, "resources", "method", "robot.resources()", "Ore nodes within your vision, nearest first.", [], "list[Entity]", "free", [], "ore = robot.resources()\nif ore:\n    robot.log(ore[0].amount)"),
 (_R, "nearest_enemy", "method", "robot.nearest_enemy()", "Closest visible enemy, or None.", [], "Entity or None", "free", [], "e = robot.nearest_enemy()\nif e:\n    robot.log(e.cls)"),
 (_R, "enemy_visible", "method", "robot.enemy_visible()", "True if any enemy is within your vision.", [], "bool", "free", [], "if robot.enemy_visible():\n    robot.retreat()"),
 (_R, "nearest_resource", "method", "robot.nearest_resource()", "Closest visible ore node, or None.", [], "Entity or None", "free", [], "n = robot.nearest_resource()\nif n:\n    robot.log(n.pos)"),
 (_R, "team_enemies", "method", "robot.team_enemies()", "Enemies currently visible to ANY robot or structure of your team (shared vision).", [], "list[Entity]", "free", [], "robot.log(len(robot.team_enemies()))"),
 (_R, "known_resources", "method", "robot.known_resources()", "Ore nodes inside territory your team has ever explored, nearest first.", [], "list[Entity]", "free", [], "for n in robot.known_resources():\n    robot.log(n.amount)"),
 (_R, "beacons", "method", "robot.beacons()", "Exploration beacons your team has seen: list of dicts with x, y, found.", [], "list[dict]", "free", [], "for b in robot.beacons():\n    robot.log(b['x'])"),
 (_R, "distance_to", "method", "robot.distance_to(x, y)", "Straight-line distance in tiles to a point.", [("x", "number", "any"), ("y", "number", "any")], "float", "free", ["TypeError if x or y is not a number."], "d = robot.distance_to(10, 10)\nrobot.log(d)"),
 (_R, "can_walk", "method", "robot.can_walk(x, y)", "True if the tile is inside the map and not rock, water or a structure.", [("x", "int", "0..map size-1"), ("y", "int", "0..map size-1")], "bool", "free", [], "if robot.can_walk(robot.x + 1, robot.y):\n    robot.move_to(robot.x + 1, robot.y)"),
 (_R, "terrain", "method", "robot.terrain(x, y)", "'grass', 'sand', 'rock', 'water', or 'unknown' if never explored.", [("x", "int", "0..map size-1"), ("y", "int", "0..map size-1")], "str", "free", [], "robot.log(robot.terrain(robot.x, robot.y))"),
 (_R, "at_hq", "method", "robot.at_hq()", "True within 2 tiles of your HQ edge (enough to deposit and recharge).", [], "bool", "free", [], "if robot.at_hq() and robot.cargo > 0:\n    robot.deposit()"),
 # ---------------- movement
 (_R, "move_to", "method", "robot.move_to(x, y)", "Plan an A* path to a tile and follow it automatically over the next ticks. Calling again with the same goal keeps the path.", [("x", "int", "0..map size-1"), ("y", "int", "0..map size-1")], "bool", "0.5 energy per grass tile (x2 on sand)", ["False: target blocked / no path / outside map (see last_error).", "Moves stop when energy runs out."], "robot.move_to(robot.hq[0] + 3, robot.hq[1] + 3)"),
 (_R, "approach", "method", "robot.approach(target, distance=1)", "Move to a free tile within `distance` tiles of a target Entity.", [("target", "Entity", "from scan()/enemies()/resources()"), ("distance", "int", ">= 1")], "bool", "movement energy", ["TypeError if target is not an Entity.", "False: target gone or no free tile."], "n = robot.nearest_resource()\nif n:\n    robot.approach(n, 1)"),
 (_R, "stop", "method", "robot.stop()", "Cancel the current path and any build job.", [], "bool", "free", [], "robot.stop()"),
 (_R, "retreat", "method", "robot.retreat()", "Move toward the free tile nearest your HQ.", [], "bool", "movement energy", ["False if no tile near the HQ is free."], "if robot.health < 30:\n    robot.retreat()"),
 # ---------------- actions
 (_R, "attack", "method", "robot.attack(target)", "Fire at a visible enemy robot/structure within attack_range. Damage = damage * 20/(20+armor), min 1.", [("target", "Entity", "enemy in range & visible")], "bool", "2 energy; weapon cooldown 2 ticks (all armed classes)", ["False: unarmed class, out of range, cooling down, not visible or already acted this tick."], "e = robot.nearest_enemy()\nif e:\n    robot.attack(e)"),
 (_R, "mine", "method", "robot.mine(node)", "Extract ore from an adjacent node into cargo (miner: 5/tick, advanced: 3/tick).", [("node", "Entity", "ore node, Chebyshev distance <= 1")], "bool", "2 energy", ["False: class cannot mine, not adjacent, cargo full or already acted."], "n = robot.nearest_resource()\nif n:\n    robot.mine(n)"),
 (_R, "deposit", "method", "robot.deposit()", "Hand cargo to your HQ (1 ore = 1 credit) or an adjacent refinery (2 ore = 1 alloy).", [], "bool", "free", ["False: empty cargo or not next to HQ/refinery."], "if robot.at_hq():\n    robot.deposit()"),
 (_R, "recharge", "method", "robot.recharge()", "Restore 24 energy while within 2 tiles of your HQ or 2 tiles of a solar panel.", [], "bool", "free (uses your action)", ["False: not near a charger or energy already full."], "if robot.energy < 30:\n    robot.recharge()"),
 (_R, "repair", "method", "robot.repair(target)", "Restore health to an adjacent friendly robot/structure (support 10, builder 6, advanced 5).", [("target", "Entity", "friendly, within 2 tiles")], "bool", "3 energy", ["False: class cannot repair, too far, or already full health."], "for a in robot.allies():\n    if a.health < a.max_health:\n        robot.repair(a)"),
 (_R, "share_energy", "method", "robot.share_energy(target, amount)", "Transfer energy (max 20) to a friendly robot within 2 tiles. Support/advanced only.", [("target", "Entity", "friendly robot"), ("amount", "number", "0..20")], "bool", "the energy transferred", ["TypeError if amount is not a number.", "False: wrong class, too far, nothing to give."], "for a in robot.allies():\n    robot.share_energy(a, 10)"),
 (_R, "build", "method", "robot.build(kind, x, y)", "Start or continue building turret/wall/solar/refinery/factory on a tile within 2 tiles of you. Costs credits on placement; keep the builder nearby until done.", [("kind", "str", "turret, wall, solar, refinery, factory"), ("x", "int", "tile within 2 of builder"), ("y", "int", "tile within 2 of builder")], "bool", "structure cost in credits + 2 energy per build tick", ["False: wrong class, unknown kind, too far, blocked, > 16 tiles from HQ, not enough credits."], "robot.build('wall', robot.x + 1, robot.y)"),
 (_R, "set_group", "method", "robot.set_group(name)", "Label this robot (max 20 chars). Scripts can be assigned to groups.", [("name", "str", "<= 20 chars")], "bool", "free", ["TypeError if name is not a string."], "robot.set_group('miners')"),
 (_R, "log", "method", "robot.log(text)", "Write a line to the execution log (same as print).", [("text", "any", "converted with str()")], "None", "free", [], "robot.log('hello')"),
 (_R, "history", "method", "robot.history()", "Recent (tick, action) pairs for this robot.", [], "list[tuple]", "free", [], "robot.log(robot.history()[-1:])"),
 # ---------------- base
 (_B, "credits", "property", "base.credits", "Credits your team holds.", [], "int", "free", [], "base.log(base.credits)"),
 (_B, "alloy", "property", "base.alloy", "Alloy produced by refineries.", [], "int", "free", [], "base.log(base.alloy)"),
 (_B, "tick", "property", "base.tick", "Current simulation tick.", [], "int", "free", [], "base.log(base.tick)"),
 (_B, "memory", "property", "base.memory", "Team-wide dict (same as robot.team_memory).", [], "dict", "free", [], "base.memory['wave'] = base.memory.get('wave', 0) + 1"),
 (_B, "hq", "property", "base.hq", "Your HQ centre (x, y).", [], "tuple or None", "free", [], "base.log(base.hq)"),
 (_B, "enemy_hq", "property", "base.enemy_hq", "Enemy HQ centre or None.", [], "tuple or None", "free", [], "base.log(base.enemy_hq)"),
 (_B, "population", "property", "base.population", "Number of living robots on your team (cap 40, queued robots count).", [], "int", "free", [], "base.log(base.population)"),
 (_B, "queue", "property", "base.queue", "Robot classes waiting in the production queue.", [], "list[str]", "free", [], "base.log(base.queue)"),
 (_B, "tech", "property", "base.tech", "Dict of research levels, e.g. {'damage': 1, ...}.", [], "dict", "free", [], "base.log(base.tech)"),
 (_B, "researching", "property", "base.researching", "Name of the technology being researched, or None.", [], "str or None", "free", [], "base.log(base.researching)"),
 (_B, "robots", "method", "base.robots(cls=None)", "Your robots as Entity views (optionally only one class). energy, cargo and group are filled in.", [("cls", "str or None", "robot class name")], "list[Entity]", "free", [], "for r in base.robots('miner'):\n    base.log(r.energy)"),
 (_B, "my_structures", "method", "base.my_structures()", "Your structures (including unfinished).", [], "list[Entity]", "free", [], "base.log(len(base.my_structures()))"),
 (_B, "count", "method", "base.count(cls)", "Number of living robots of a class.", [("cls", "str", "robot class name")], "int", "free", [], "base.log(base.count('miner'))"),
 (_B, "can_afford", "method", "base.can_afford(what)", "True if credits cover a robot class or structure kind.", [("what", "str", "class or structure name")], "bool", "free", [], "if base.can_afford('miner'):\n    base.build_robot('miner')"),
 (_B, "build_robot", "method", "base.build_robot(cls)", "Queue a robot. Costs credits now; produced after the class build time (one at a time, +1 slot per factory).", [("cls", "str", "scout, miner, builder, defender, support, transport, advanced")], "bool", "class cost in credits", ["ValueError for an unknown class.", "False: not enough credits, queue full (6) or population cap (40)."], "if base.count('miner') < 3:\n    base.build_robot('miner')"),
 (_B, "research", "method", "base.research(name)", "Start a technology level (30 ticks, one at a time).", [("name", "str", "damage, armor, speed, vision, capacity, energy")], "bool", "50-300 credits depending on level", ["ValueError for an unknown tech.", "False: max level, already researching, not enough credits."], "base.research('armor')"),
 (_B, "set_group", "method", "base.set_group(robot_id, group)", "Label one of your robots by id.", [("robot_id", "int", "an id from base.robots()"), ("group", "str", "<= 20 chars")], "bool", "free", [], "for r in base.robots('defender'):\n    base.set_group(r.id, 'guards')"),
 (_B, "assign_script", "method", "base.assign_script(key, script_name)", "Change which script runs for 'class:miner', 'group:alpha' or 'robot:12'.", [("key", "str", "class:<cls> | group:<name> | robot:<id> | default"), ("script_name", "str", "an existing script file")], "bool", "free", ["ValueError if the key format is wrong."], "base.assign_script('class:miner', 'main.py')"),
 (_B, "log", "method", "base.log(text)", "Write a line to the log.", [("text", "any", "converted with str()")], "None", "free", [], "base.log('commander online')"),
 # ---------------- entity
 (_E, "id", "property", "entity.id", "Unique id of the thing you scanned.", [], "int", "free", [], "for e in robot.scan():\n    robot.log(e.id)"),
 (_E, "kind", "property", "entity.kind", "'robot', 'structure', 'hq' or 'resource'.", [], "str", "free", [], "for e in robot.scan():\n    robot.log(e.kind)"),
 (_E, "cls", "property", "entity.cls", "Robot class, structure kind, or 'ore'.", [], "str", "free", [], "for e in robot.scan():\n    robot.log(e.cls)"),
 (_E, "team", "property", "entity.team", "Team number, or None for resources.", [], "int or None", "free", [], "for e in robot.scan():\n    robot.log(e.team)"),
 (_E, "x", "property", "entity.x", "Tile column.", [], "int", "free", [], "for e in robot.scan():\n    robot.log(e.x)"),
 (_E, "y", "property", "entity.y", "Tile row.", [], "int", "free", [], "for e in robot.scan():\n    robot.log(e.y)"),
 (_E, "pos", "property", "entity.pos", "(x, y) tuple.", [], "tuple", "free", [], "for e in robot.scan():\n    robot.log(e.pos)"),
 (_E, "health", "property", "entity.health", "Current hit points (None for resources).", [], "float or None", "free", [], "for e in robot.enemies():\n    robot.log(e.health)"),
 (_E, "max_health", "property", "entity.max_health", "Maximum hit points.", [], "float or None", "free", [], "for e in robot.enemies():\n    robot.log(e.max_health)"),
 (_E, "amount", "property", "entity.amount", "Ore left in a resource node (None otherwise).", [], "int or None", "free", [], "for n in robot.resources():\n    robot.log(n.amount)"),
 (_E, "distance", "property", "entity.distance", "Distance from the robot that scanned it.", [], "float", "free", [], "for e in robot.scan():\n    robot.log(e.distance)"),
 (_E, "ally", "property", "entity.ally", "True friendly, False enemy, None for resources.", [], "bool or None", "free", [], "for e in robot.scan():\n    robot.log(e.ally)"),
 (_E, "built", "property", "entity.built", "For structures: whether construction is finished.", [], "bool or None", "free", [], "for s in robot.structures():\n    robot.log(s.built)"),
 (_E, "energy", "property", "entity.energy", "Energy (only filled in by base.robots()).", [], "float or None", "free", [], "robot.log('energy')"),
 (_E, "cargo", "property", "entity.cargo", "Cargo (only filled in by base.robots()).", [], "int or None", "free", [], "robot.log('cargo')"),
 (_E, "group", "property", "entity.group", "Group label (only filled in by base.robots()).", [], "str or None", "free", [], "robot.log('group')"),
 (_E, "dist_to", "method", "entity.dist_to(x, y)", "Distance from this entity to a point.", [("x", "number", "any"), ("y", "number", "any")], "float", "free", [], "for e in robot.scan():\n    robot.log(e.dist_to(0, 0))"),
]

_KEYS = ("owner", "name", "kind", "signature", "description", "params", "returns", "cost", "errors", "example_body")


def get_spec():
    out = []
    for row in _SPEC:
        d = dict(zip(_KEYS, row))
        d["params"] = [dict(name=p[0], type=p[1], valid=p[2]) for p in d["params"]]
        if d["owner"] == "base":
            d["example"] = "def commander(base):\n" + _indent(d["example_body"])
        else:
            d["example"] = "def update(robot):\n" + _indent(d["example_body"])
        out.append(d)
    return out


def _indent(body):
    return "\n".join("    " + ln for ln in body.split("\n")) + "\n"


CLASS_NOTES = {
    "mine": ["miner", "advanced"], "build": ["builder", "advanced"], "attack": ["scout", "defender", "advanced"],
    "repair": ["support", "builder", "advanced"], "share_energy": ["support", "advanced"],
}
