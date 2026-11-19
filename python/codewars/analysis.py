"""Post-match analysis: explains why a strategy worked or failed using recorded stats."""
from . import modes


def analyze(sim):
    t = sim.teams[0]
    s = t.stats
    out = []

    def add(kind, text):
        out.append(dict(kind=kind, text=text))

    res = sim.result
    if res:
        add("good" if res.get("winner") == 0 else "bad", res["reason"] + " (tick %d)." % res.get("tick", sim.tick))
    ticks = max(1, sim.tick)
    nrob = max(1, s["peak_robots"])
    idle = s["idle_ticks"] / float(max(1, s["robot_ticks"]))
    if s["ore_mined"] > 0 and s["ore_delivered"] < s["ore_mined"] * 0.6:
        add("bad", "You mined %d ore but only delivered %d. Ore in cargo is worthless until deposited; return when cargo is near capacity." % (s["ore_mined"], s["ore_delivered"]))
    elif s["ore_delivered"] > 0:
        add("good", "Economy: %d ore delivered (%.0f per 100 ticks)." % (s["ore_delivered"], 100.0 * s["ore_delivered"] / ticks))
    if s["empty_energy_ticks"] > 0.08 * max(1, s["robot_ticks"]):
        add("bad", "Robots spent %d robot-ticks with no energy. Call recharge() near the HQ or build solar panels before energy hits 0." % s["empty_energy_ticks"])
    if idle > 0.5:
        add("tip", "Robots were idle roughly %.0f%% of the time. Give every robot a fallback behaviour (e.g. patrol or mine) in update()." % (idle * 100))
    if s["script_errors"]:
        add("bad", "Your scripts raised %d errors (%d budget overruns). Check the execution log for the failing line." % (s["script_errors"], s["budget_overruns"]))
    else:
        add("good", "No script errors or budget overruns - reliable automation.")
    if sim.has_enemy:
        if s["damage_dealt"] > 0:
            ratio = s["damage_dealt"] / max(1.0, s["damage_taken"])
            add("good" if ratio >= 1 else "bad", "Damage dealt %.0f vs taken %.0f (ratio %.2f). %s" % (
                s["damage_dealt"], s["damage_taken"], ratio,
                "You traded efficiently." if ratio >= 1 else "Fight near turrets/support and focus fire so you trade better."))
        else:
            add("bad", "You dealt no damage. Armed classes: scout, defender, advanced. Use robot.attack(target).")
        turret_deaths = sum(v for (c, cause), v in t.lost_by_cause.items() if cause == "turret")
        if turret_deaths >= 2:
            add("bad", "%d robots died to turrets. Turrets reach 6 tiles; outrange them with massed units or approach from the flank." % turret_deaths)
        for (cls, cause), v in sorted(t.lost_by_cause.items(), key=lambda kv: -kv[1])[:1]:
            if v >= 3:
                add("tip", "Most losses were %s units (%d). Pair them with support robots or keep them behind defenders." % (cls, v))
        if sum(1 for r in sim.robots.values() if r.team == 0 and r.cls == "support") == 0 and s["losses"] >= 4:
            add("tip", "You lost %d robots and fielded no support. A support robot repairs 10 HP/tick." % s["losses"])
        if sum(t.tech.values()) == 0 and s["credits_spent"] > 400:
            add("tip", "You never researched upgrades. base.research('armor') or 'damage' compounds over a long fight.")
        e = sim.teams[1]
        add("info", "Enemy lost %d robots and %d structures; produced %d robots." % (e.stats["losses"], e.stats["structures_lost"], e.stats["produced"]))
    if sim.mode == "exploration":
        add("info", "Beacons recovered: %d of %d." % (s["beacons"], len(sim.beacons)))
    if sim.mode == "racing":
        add("info", "Checkpoints: %d of %d in %d ticks." % (s["checkpoints"], len(sim.checkpoints), sim.tick))
    if sim.mode == "factory":
        add("info", "Alloy produced: %d. Refineries convert 2 ore into 1 alloy - more miners/transports means more throughput." % s["alloy_made"])
    return dict(items=out, stars=modes.stars(sim), score=modes._score(sim, 0), stats={k: (round(v, 1) if isinstance(v, float) else v) for k, v in s.items()})
