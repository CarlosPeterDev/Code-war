"""Static game data: terrain, robot classes, structures, tech, difficulty, worlds."""

GRASS, SAND, ROCK, WATER = 0, 1, 2, 3
TERRAIN_COST = {GRASS: 1.0, SAND: 2.0}
BLOCKED_TERRAIN = {ROCK, WATER}

# speed = movement points gained per tick; a tile costs its terrain cost.
CLASSES = {
    "scout": dict(hp=40, energy=60, speed=2.0, vision=9, capacity=0, damage=4, range=2.0,
                  cooldown=2, armor=0, mine=0, build=0, repair=0, cost=30, build_time=4,
                  desc="Fast, long-sight recon unit with a weak sidearm."),
    "miner": dict(hp=70, energy=80, speed=0.9, vision=5, capacity=30, damage=0, range=0,
                  cooldown=1, armor=1, mine=5, build=0, repair=0, cost=50, build_time=6,
                  desc="Harvests ore nodes and hauls a small load home."),
    "builder": dict(hp=80, energy=90, speed=0.9, vision=5, capacity=0, damage=0, range=0,
                    cooldown=1, armor=1, mine=0, build=1, repair=6, cost=70, build_time=7,
                    desc="Constructs turrets, walls, solar panels, refineries and factories."),
    "defender": dict(hp=160, energy=100, speed=0.8, vision=6, capacity=0, damage=14, range=4.0,
                     cooldown=2, armor=6, mine=0, build=0, repair=0, cost=90, build_time=8,
                     desc="Heavily armoured front-line fighter."),
    "support": dict(hp=70, energy=120, speed=1.0, vision=6, capacity=0, damage=0, range=0,
                    cooldown=1, armor=1, mine=0, build=0, repair=10, cost=80, build_time=8,
                    desc="Repairs allies and shares energy."),
    "transport": dict(hp=90, energy=100, speed=1.6, vision=5, capacity=80, damage=0, range=0,
                      cooldown=1, armor=2, mine=0, build=0, repair=0, cost=90, build_time=8,
                      desc="Big-capacity fast hauler; cannot mine on its own."),
    "advanced": dict(hp=120, energy=130, speed=1.1, vision=7, capacity=20, damage=10, range=4.0,
                     cooldown=2, armor=3, mine=3, build=1, repair=5, cost=160, build_time=12,
                     desc="Expensive generalist that can fight, mine, build and repair."),
}

STRUCTURES = {
    "turret": dict(cost=60, hp=120, build_time=10, range=6.0, damage=9, cooldown=2, armor=2,
                   desc="Auto-fires at visible enemies in range."),
    "wall": dict(cost=10, hp=150, build_time=3, range=0, damage=0, cooldown=1, armor=4,
                 desc="Blocks movement."),
    "solar": dict(cost=40, hp=60, build_time=6, range=0, damage=0, cooldown=1, armor=0,
                  desc="Recharges nearby friendly robots (+6 energy/tick within 2 tiles)."),
    "refinery": dict(cost=120, hp=100, build_time=12, range=0, damage=0, cooldown=1, armor=1,
                     desc="Accepts ore deposits and turns 2 ore into 1 alloy."),
    "factory": dict(cost=150, hp=140, build_time=14, range=0, damage=0, cooldown=1, armor=2,
                    desc="Adds a second robot production slot."),
}

TECH = {
    "damage": dict(levels=3, costs=[100, 200, 300], per_level=0.15, desc="+15% weapon damage per level."),
    "armor": dict(levels=3, costs=[100, 200, 300], per_level=2, desc="+2 armor per level."),
    "speed": dict(levels=3, costs=[80, 160, 240], per_level=0.10, desc="+10% speed per level."),
    "vision": dict(levels=2, costs=[80, 160], per_level=1, desc="+1 vision radius per level."),
    "capacity": dict(levels=3, costs=[60, 120, 180], per_level=0.25, desc="+25% cargo capacity per level."),
    "energy": dict(levels=3, costs=[80, 160, 240], per_level=0.20, desc="+20% max energy per level."),
}
RESEARCH_TICKS = 30

COSTS = dict(move_per_tile=0.5, attack=2.0, mine=2.0, build=2.0, repair=3.0, deposit=0.0,
             recharge_share=0.0, scan=0.0)
HQ_HP = 500
HQ_RECHARGE = 8.0       # energy per tick within HQ radius
HQ_RADIUS = 2.5
SOLAR_RECHARGE = 6.0
ORE_PER_CREDIT = 1
MAX_TICKS_DEFAULT = 3000

# level: ai_level 0..4 drives opponent behaviour (see ai.py)
DIFFICULTY = {
    "beginner": dict(index=1, ai_level=0, start_credits=400, ore_mult=1.5, ai_react=4, map_size=28,
                     time_mult=1.5, assist=True, line_budget=3000,
                     blurb="Passive opponent, generous economy, guided hints."),
    "easy": dict(index=2, ai_level=1, start_credits=300, ore_mult=1.25, ai_react=3, map_size=32,
                 time_mult=1.25, assist=True, line_budget=3000,
                 blurb="Opponent expands slowly and attacks in small groups."),
    "normal": dict(index=3, ai_level=2, start_credits=250, ore_mult=1.0, ai_react=2, map_size=36,
                   time_mult=1.0, assist=False, line_budget=2500,
                   blurb="Balanced opponent with defences and coordinated waves."),
    "hard": dict(index=4, ai_level=3, start_credits=200, ore_mult=1.0, ai_react=1, map_size=40,
                 time_mult=0.9, assist=False, line_budget=2000,
                 blurb="Scouting, harassment, focus-fire and upgrades."),
    "expert": dict(index=5, ai_level=4, start_credits=200, ore_mult=0.9, ai_react=1, map_size=44,
                   time_mult=0.8, assist=False, line_budget=1500,
                   blurb="Adaptive opponent that counters your strategy. Tight script budget."),
}

WORLDS = {
    "ironvale": dict(name="Ironvale", sand=0.12, rock=0.16, water=0.06, ore_clusters=5,
                     palette=dict(ground="#4f7a3a", sand="#b8a15f", rock="#6b6f75", water="#2c5f8f", sky="#9cc7e8"),
                     blurb="Rolling grassland with scattered rock walls."),
    "dune_reach": dict(name="Dune Reach", sand=0.55, rock=0.12, water=0.02, ore_clusters=4,
                       palette=dict(ground="#c8a85a", sand="#e2c47a", rock="#8a6a4a", water="#3a7a8f", sky="#e9c98f"),
                       blurb="Slow sand everywhere; mobility matters."),
    "frostline": dict(name="Frostline", sand=0.05, rock=0.22, water=0.16, ore_clusters=6,
                      palette=dict(ground="#c9dce8", sand="#a9bfd0", rock="#5f7183", water="#3b6a9a", sky="#cfe4f2"),
                      blurb="Frozen lakes and ridges create chokepoints."),
    "ember_fields": dict(name="Ember Fields", sand=0.2, rock=0.28, water=0.0, ore_clusters=4,
                         palette=dict(ground="#4a3f3a", sand="#7a5a3a", rock="#2c2a2c", water="#a03a1a", sky="#6a3a2a"),
                         blurb="Dense rock mazes; few resources."),
    "verdant_basin": dict(name="Verdant Basin", sand=0.08, rock=0.1, water=0.22, ore_clusters=7,
                          palette=dict(ground="#3f8a4a", sand="#c4b46a", rock="#5d6a5d", water="#2a6fa0", sky="#a8dcc0"),
                          blurb="Rich ore, big lakes, long detours."),
}
