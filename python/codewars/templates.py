"""Script templates (also the default scripts used by the 'starter army' button)."""

TEMPLATES = {
"blank.py": ('Blank', '''def update(robot):
    pass
'''),
"miner.py": ('Miner: mine, haul, recharge', '''def update(robot):
    # 1. keep energy healthy
    if robot.energy < 20:
        if robot.at_hq():
            robot.recharge()
        else:
            robot.retreat()
        return
    # 2. go home when the cargo is nearly full (or nothing is left to mine)
    if robot.cargo >= robot.capacity - 4 or (robot.cargo > 0 and not robot.known_resources()):
        if robot.at_hq():
            robot.deposit()
        else:
            robot.retreat()
        return
    # 3. otherwise mine the nearest known ore
    ore = robot.known_resources()
    if not ore:
        # nothing known: wander to a new spot so we reveal more of the map
        mem = robot.memory
        if 'wp' not in mem or robot.distance_to(mem['wp'][0], mem['wp'][1]) < 3:
            import random
            mem['wp'] = (random.randint(2, 28), random.randint(2, 28))
        if not robot.move_to(mem['wp'][0], mem['wp'][1]):
            mem.pop('wp')
        return
    node = ore[0]
    if max(abs(node.x - robot.x), abs(node.y - robot.y)) <= 1:
        robot.mine(node)
    else:
        robot.approach(node, 1)
'''),
"scout.py": ('Scout: explore the map', '''CORNERS = [(2, 2), (30, 2), (30, 30), (2, 30)]

def update(robot):
    mem = robot.memory
    i = mem.get('leg', 0)
    gx, gy = CORNERS[i % 4]
    if robot.distance_to(gx, gy) < 3 or not robot.moving and not robot.move_to(gx, gy):
        mem['leg'] = i + 1
    elif not robot.moving:
        robot.move_to(gx, gy)
    foe = robot.nearest_enemy()
    if foe and foe.distance <= robot.attack_range:
        robot.attack(foe)
'''),
"defender.py": ('Defender: guard and strike', '''def update(robot):
    if robot.health < robot.max_health * 0.3 or robot.energy < 15:
        if robot.at_hq() and robot.energy < robot.max_energy:
            robot.recharge()
        else:
            robot.retreat()
        return
    foes = robot.team_enemies()
    if foes:
        target = min(foes, key=lambda e: (e.health, e.distance))
        if target.distance <= robot.attack_range:
            robot.attack(target)
        elif target.distance < 10:
            robot.approach(target, 3)
        return
    hx, hy = robot.hq
    ex, ey = robot.enemy_hq if robot.enemy_hq else (hx, hy)
    gx = hx + (4 if ex > hx else -4)
    gy = hy + (4 if ey > hy else -4)
    if robot.distance_to(gx, gy) > 2:
        robot.move_to(gx, gy)
'''),
"builder.py": ('Builder: turrets near the HQ', '''def update(robot):
    hx, hy = robot.hq
    ex, ey = robot.enemy_hq if robot.enemy_hq else (hx, hy)
    sx = 1 if ex > hx else -1
    sy = 1 if ey > hy else -1
    sites = [(hx + 5 * sx, hy + 3 * sy), (hx + 3 * sx, hy + 5 * sy), (hx + 5 * sx, hy + 5 * sy)]
    mem = robot.memory
    n = mem.get('built', 0)
    if n >= len(sites):
        return
    tx, ty = sites[n]
    if robot.distance_to(tx, ty) > 2:
        robot.move_to(tx, ty + 1)
        return
    if robot.build('turret', tx, ty):
        pass
    elif robot.last_error.startswith('cmd: build tile'):
        mem['built'] = n + 1
    st = [s for s in robot.structures() if s.cls == 'turret' and s.pos == (tx, ty) and s.built]
    if st:
        mem['built'] = n + 1
'''),
"support.py": ('Support: heal allies', '''def update(robot):
    hurt = [a for a in robot.allies() if a.health < a.max_health * 0.85]
    if hurt:
        t = min(hurt, key=lambda a: a.health / a.max_health)
        if t.distance <= 2:
            robot.repair(t)
        else:
            robot.approach(t, 1)
        return
    hx, hy = robot.hq
    if robot.distance_to(hx + 3, hy + 3) > 3:
        robot.move_to(hx + 3, hy + 3)
'''),
"commander.py": ('Commander: build order', '''def commander(base):
    wanted = [('miner', 3), ('defender', 2), ('builder', 1), ('defender', 5), ('support', 1), ('defender', 8)]
    for cls, n in wanted:
        if base.count(cls) + base.queue.count(cls) < n:
            base.build_robot(cls)
            break
    if base.researching is None and base.credits > 300:
        for tech in ('damage', 'armor', 'speed'):
            if base.research(tech):
                break
'''),
"racer.py": ('Racer: follow checkpoints', '''def update(robot):
    cp = robot.checkpoint
    if cp:
        robot.move_to(cp[0], cp[1])
'''),
"attacker.py": ('Attacker: wave assault', '''def update(robot):
    if robot.health < robot.max_health * 0.25 or robot.energy < 12:
        robot.retreat()
        if robot.at_hq():
            robot.recharge()
        return
    foes = robot.team_enemies()
    if foes:
        t = min(foes, key=lambda e: (e.health, e.distance))
        if t.distance <= robot.attack_range:
            robot.attack(t)
            return
        if t.distance < 12:
            robot.approach(t, max(1, int(robot.attack_range) - 1))
            return
    if robot.tick < 600 or robot.memory.get('wait', True) and robot.team_memory.get('army', 0) < 5:
        hx, hy = robot.hq
        robot.team_memory['army'] = robot.team_memory.get('army', 0)
        if robot.distance_to(hx + 5, hy + 5) > 3:
            robot.move_to(hx + 5, hy + 5)
        return
    ex, ey = robot.enemy_hq
    robot.move_to(ex - 4 if ex > robot.x else ex + 4, ey - 4 if ey > robot.y else ey + 4)
'''),
}

STARTER_ASSIGN = {
    "class:miner": "miner.py", "class:scout": "scout.py", "class:defender": "defender.py",
    "class:builder": "builder.py", "class:support": "support.py", "class:advanced": "defender.py",
    "class:transport": "blank.py", "commander": "commander.py",
}


def get_templates():
    return [dict(name=k, title=v[0], source=v[1]) for k, v in TEMPLATES.items()]


def starter_scripts():
    return {k: v[1] for k, v in TEMPLATES.items()}
