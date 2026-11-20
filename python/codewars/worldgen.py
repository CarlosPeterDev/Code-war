"""Deterministic map generation and grid pathfinding."""
import heapq
import math
import random

from .defs import BLOCKED_TERRAIN, GRASS, ROCK, SAND, TERRAIN_COST, WATER, WORLDS

_DIRS8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def _value_noise(w, h, rng, scale):
    gw, gh = w // scale + 3, h // scale + 3
    grid = [[rng.random() for _ in range(gw)] for _ in range(gh)]

    def smooth(t):
        return t * t * (3 - 2 * t)

    out = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            fx, fy = x / scale, y / scale
            x0, y0 = int(fx), int(fy)
            tx, ty = smooth(fx - x0), smooth(fy - y0)
            a = grid[y0][x0] * (1 - tx) + grid[y0][x0 + 1] * tx
            b = grid[y0 + 1][x0] * (1 - tx) + grid[y0 + 1][x0 + 1] * tx
            out[y][x] = a * (1 - ty) + b * ty
    return out


def passable_terrain(t):
    return t not in BLOCKED_TERRAIN


def find_path(grid, blocked, start, goal, max_expand=6000, penalty=None):
    """A* over an 8-connected grid. `blocked` is a set of (x,y); returns list of tiles
    excluding start, or None. `penalty(x,y)` adds extra cost (used by AI to avoid turrets)."""
    h, w = len(grid), len(grid[0])
    if start == goal:
        return []
    gx, gy = goal

    def ok(x, y):
        return 0 <= x < w and 0 <= y < h and grid[y][x] not in BLOCKED_TERRAIN and (x, y) not in blocked

    if not (0 <= gx < w and 0 <= gy < h) or grid[gy][gx] in BLOCKED_TERRAIN:
        return None
    if goal in blocked:
        return None
    openh = [(0.0, 0.0, start)]
    came = {}
    gscore = {start: 0.0}
    n = 0
    while openh:
        _, g, cur = heapq.heappop(openh)
        if cur == goal:
            path = []
            while cur != start:
                path.append(cur)
                cur = came[cur]
            path.reverse()
            return path
        if g > gscore.get(cur, 1e18):
            continue
        n += 1
        if n > max_expand:
            return None
        cx, cy = cur
        for dx, dy in _DIRS8:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < w and 0 <= ny < h) or grid[ny][nx] in BLOCKED_TERRAIN:
                continue
            if (nx, ny) in blocked:
                continue
            if dx and dy and (not ok(cx + dx, cy) or not ok(cx, cy + dy)):
                continue  # no corner cutting
            step = TERRAIN_COST.get(grid[ny][nx], 1.0) * (1.4142 if dx and dy else 1.0)
            if penalty:
                step += penalty(nx, ny)
            ng = g + step
            if ng < gscore.get((nx, ny), 1e18):
                gscore[(nx, ny)] = ng
                came[(nx, ny)] = cur
                hh = max(abs(nx - gx), abs(ny - gy)) + 0.4142 * min(abs(nx - gx), abs(ny - gy))
                heapq.heappush(openh, (ng + hh, ng, (nx, ny)))
    return None


def reachable_set(grid, start, blocked=frozenset()):
    """Tiles reachable from start using the same movement rules as find_path (no corner cutting)."""
    h, w = len(grid), len(grid[0])

    def ok(x, y):
        return 0 <= x < w and 0 <= y < h and grid[y][x] not in BLOCKED_TERRAIN and (x, y) not in blocked

    seen = {start}
    stack = [start]
    while stack:
        cx, cy = stack.pop()
        for dx, dy in _DIRS8:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in seen or not ok(nx, ny):
                continue
            if dx and dy and (not ok(cx + dx, cy) or not ok(cx, cy + dy)):
                continue
            seen.add((nx, ny))
            stack.append((nx, ny))
    return seen


def generate_world(world_id, size, seed, ore_mult=1.0, two_bases=True):
    """Return dict(grid, hq=[(x,y),(x,y)], ore=[...], trees=[...], size). Guarantees HQs connected."""
    spec = WORLDS[world_id]
    for attempt in range(40):
        rng = random.Random(seed * 1009 + attempt)
        w = h = size
        n1 = _value_noise(w, h, rng, 6)
        n2 = _value_noise(w, h, rng, 4)
        n3 = _value_noise(w, h, rng, 9)
        grid = [[GRASS] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                v = n1[y][x]
                if n3[y][x] < spec["water"] * 1.6 and v < 0.5:
                    grid[y][x] = WATER
                elif n2[y][x] > 1 - spec["rock"] * 1.8:
                    grid[y][x] = ROCK
                elif v > 1 - spec["sand"] * 1.4 or (spec["sand"] > 0.4 and v > 0.3):
                    grid[y][x] = SAND
        m = 4
        hq_a = (m + 1, m + 1)
        hq_b = (w - m - 2, h - m - 2)
        for hx, hy in (hq_a, hq_b):
            for y in range(hy - 4, hy + 5):
                for x in range(hx - 4, hx + 5):
                    if 0 <= x < w and 0 <= y < h:
                        grid[y][x] = GRASS if math.hypot(x - hx, y - hy) <= 4.2 else grid[y][x]
        # borders stay walkable-ish: leave as generated
        reach = reachable_set(grid, hq_a)
        if hq_b not in reach:
            continue
        ore = []
        occupied = set()
        clusters = spec["ore_clusters"]
        tries = 0
        while len(ore) < clusters * 3 and tries < 800:
            tries += 1
            cx, cy = rng.randrange(3, w - 3), rng.randrange(3, h - 3)
            if (cx, cy) not in reach or grid[cy][cx] in BLOCKED_TERRAIN:
                continue
            if math.hypot(cx - hq_a[0], cy - hq_a[1]) < 6 or math.hypot(cx - hq_b[0], cy - hq_b[1]) < 6:
                if len(ore) >= 2:
                    continue
            for _ in range(rng.randint(2, 4)):
                ox, oy = cx + rng.randint(-1, 1), cy + rng.randint(-1, 1)
                if 0 <= ox < w and 0 <= oy < h and grid[oy][ox] not in BLOCKED_TERRAIN \
                        and (ox, oy) not in occupied and (ox, oy) in reach:
                    occupied.add((ox, oy))
                    ore.append(dict(x=ox, y=oy, amount=int(rng.randint(120, 220) * ore_mult)))
        # guarantee a sustainable amount of ore near each HQ (>= 5 nodes within 11 tiles)
        for hx, hy in (hq_a, hq_b):
            ring = [(hx + dx, hy + dy) for dx in range(-9, 10) for dy in range(-9, 10)
                    if 5 <= max(abs(dx), abs(dy)) <= 9]
            rng.shuffle(ring)
            # at least two nodes inside the HQ's starting vision (radius 7) so miners have work at tick 0
            close = [(hx + dx, hy + dy) for dx in range(-6, 7) for dy in range(-6, 7)
                     if 4 <= max(abs(dx), abs(dy)) <= 6 and math.hypot(dx, dy) <= 6.4]
            rng.shuffle(close)
            near = sum(1 for o in ore if math.hypot(o["x"] - hx, o["y"] - hy) <= 6.4)
            for ox, oy in close:
                if near >= 2:
                    break
                if 0 <= ox < w and 0 <= oy < h and grid[oy][ox] not in BLOCKED_TERRAIN \
                        and (ox, oy) not in occupied and (ox, oy) in reach:
                    occupied.add((ox, oy))
                    ore.append(dict(x=ox, y=oy, amount=int(rng.randint(220, 320) * ore_mult)))
                    near += 1
            have = sum(1 for o in ore if math.hypot(o["x"] - hx, o["y"] - hy) <= 11)
            for ox, oy in ring:
                if have >= 5:
                    break
                if 0 <= ox < w and 0 <= oy < h and grid[oy][ox] not in BLOCKED_TERRAIN \
                        and (ox, oy) not in occupied and (ox, oy) in reach:
                    occupied.add((ox, oy))
                    ore.append(dict(x=ox, y=oy, amount=int(rng.randint(220, 320) * ore_mult)))
                    have += 1
        trees = []
        for _ in range(w * h // 18):
            tx, ty = rng.randrange(w), rng.randrange(h)
            if grid[ty][tx] == GRASS and (tx, ty) not in occupied and \
                    math.hypot(tx - hq_a[0], ty - hq_a[1]) > 5 and math.hypot(tx - hq_b[0], ty - hq_b[1]) > 5:
                trees.append((tx, ty))
        return dict(grid=grid, hq=[hq_a, hq_b], ore=ore, trees=trees, size=size, world=world_id, seed=seed)
    raise RuntimeError("could not generate connected world")
