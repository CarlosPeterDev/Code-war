import json

import pytest

from codewars import bridge, lessons, modes
from codewars import sim as S

REF = {
 "l01": "def energy_percent(energy, max_energy):\n    return energy * 100 // max_energy\n",
 "l02": "def describe(x):\n    if isinstance(x, bool):\n        return 'bool'\n    if isinstance(x, int):\n        return 'int'\n    if isinstance(x, float):\n        return 'float'\n    if isinstance(x, str):\n        return 'str'\n    if isinstance(x, list):\n        return 'list'\n    return 'dict'\n",
 "l03": "def should_retreat(health, energy):\n    return health < 30 or energy < 15\n",
 "l04": "def count_class(robots, cls):\n    n = 0\n    for r in robots:\n        if r['cls'] == cls:\n            n += 1\n    return n\n",
 "l05": "def damage_after_armor(damage, armor):\n    return round(max(1, damage * 20 / (20 + armor)), 2)\n",
 "l06": "def healthiest(robots):\n    if not robots:\n        return None\n    return max(robots, key=lambda r: r['hp'])['id']\n",
 "l07": "def tally(names):\n    d = {}\n    for n in names:\n        d[n] = d.get(n, 0) + 1\n    return d\n",
 "l08": "def report(name, hp):\n    return f\"{name.upper()}: {hp} HP\"\n",
 "l09": "def update(robot):\n    for dx, dy in ((9, 9), (9, 0), (0, 9), (-9, 9), (9, -9)):\n        if robot.move_to(robot.x + dx, robot.y + dy):\n            return\n",
 "l10": "def update(robot):\n    if robot.energy < 20:\n        if robot.at_hq():\n            robot.recharge()\n        else:\n            robot.retreat()\n        return\n    if robot.cargo >= robot.capacity - 4:\n        if robot.at_hq():\n            robot.deposit()\n        else:\n            robot.retreat()\n        return\n    ore = robot.known_resources()\n    if ore:\n        n = ore[0]\n        if max(abs(n.x - robot.x), abs(n.y - robot.y)) <= 1:\n            robot.mine(n)\n        else:\n            robot.approach(n, 1)\n",
 "l11": "def update(robot):\n    if robot.energy < robot.max_energy and robot.at_hq():\n        robot.recharge()\n",
 "l12": "def update(robot):\n    foes = robot.team_enemies()\n    if foes:\n        foe = foes[0]\n        if foe.distance <= robot.attack_range:\n            robot.attack(foe)\n        else:\n            robot.approach(foe, 2)\n",
 "l13": "def update(robot):\n    robot.memory['steps'] = robot.memory.get('steps', 0) + 1\n",
 "l14": "def update(robot):\n    if robot.cls == 'miner':\n        robot.set_group('workers')\n    elif robot.cls == 'scout':\n        robot.set_group('eyes')\n",
 "l15": "def update(robot):\n    hx, hy = robot.hq\n    robot.team_memory['rally'] = (hx + 3, hy + 2)\n    robot.move_to(hx + 3, hy + 2)\n",
}


def test_every_lesson_has_a_reference_solution():
    assert set(REF) == {l["id"] for l in lessons.LESSONS}


@pytest.mark.parametrize("lid", sorted(REF))
def test_reference_solution_completes_lesson(lid):
    r = lessons.run_lesson(lid, REF[lid])
    assert r["ok"], r


@pytest.mark.parametrize("lid", sorted(REF))
def test_starter_code_does_not_complete_lesson(lid):
    assert not lessons.run_lesson(lid, lessons.BY_ID[lid]["starter"])["ok"]


def test_lesson_reports_runtime_errors_and_unsafe_code():
    r = lessons.run_lesson("l09", "def update(robot):\n    x = 1 / 0\n")
    assert not r["ok"] and "ZeroDivisionError" in r["message"]
    r = lessons.run_lesson("l09", "import os\n")
    assert not r["ok"] and "not allowed" in r["message"]
    r = lessons.run_lesson("l01", "def energy_percent(a, b):\n    while True:\n        pass\n")
    assert not r["ok"]


def test_lesson_covers_required_topics():
    titles = " ".join(l["title"].lower() + " " + l["section"].lower() for l in lessons.LESSONS)
    for topic in ("variables", "types", "conditions", "loops", "functions", "lists", "dictionaries", "strings",
                  "move", "mine", "energy", "combat", "memory", "groups", "team memory", "multi-robot"):
        assert topic in titles, topic


@pytest.mark.parametrize("m", modes.CAMPAIGN, ids=lambda m: m["id"])
def test_campaign_missions_load_and_run(m):
    sim = S.Sim(modes.campaign_config(m["id"]))
    sim.set_scripts({}, {})
    sim.step(3)
    assert sim.objectives and sim.tick == 3


def test_campaign_progresses_in_difficulty():
    order = ["beginner", "easy", "normal", "hard", "expert"]
    idx = [order.index(m["difficulty"]) for m in modes.CAMPAIGN]
    assert idx[0] == 0 and idx[-1] == 4 and max(idx) == 4
    assert {m["mode"] for m in modes.CAMPAIGN} == {"robot_wars", "base_commander", "exploration", "factory", "racing"}


def test_bridge_lessons_and_previews():
    assert len(json.loads(bridge.lesson_list())) == 15
    assert json.loads(bridge.run_lesson("l03", REF["l03"]))["ok"]
    pv = json.loads(bridge.world_preview("frostline", 32, 3))
    assert len(pv["grid"]) == 32 and len(pv["hq"]) == 2
    g = json.loads(bridge.start_campaign("c05", "{}", "{}"))
    assert g["snapshot"]["objectives"] is not None
