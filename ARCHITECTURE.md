# Architecture

## Overview
```
Flutter UI (Dart)  <--MethodChannel "codewars/py"-->  Kotlin MainActivity  -->  Chaquopy CPython 3.12
      |                                                                          codewars.bridge (JSON in/out)
      +-- WebView (three.js renderer, JS channel "CWChannel") <-- snapshots (JSON) from the engine each tick
```
The simulation is authoritative and lives in Python. After each step Dart receives a **fog-filtered snapshot**, shows the HUD
and forwards the same JSON to the renderer (`CW.update`). The renderer never sees hidden enemies.

## Engine choices and trade-offs
- **3D**: Flutter has no mature 3D engine, so the renderer is three.js (real meshes, PBR materials, textures, directional light
  with shadow maps, hemisphere light, perspective camera, skeletal animation) bundled offline into one HTML file with esbuild and
  shown in `webview_flutter`. Trade-off: the WebView adds a process boundary and its performance depends on the device GPU/WebView.
- **Python**: Chaquopy embeds real CPython **3.12** (arm64-v8a only; Chaquopy has no 32-bit build for 3.12). Trade-off: larger APK,
  64-bit devices only.
- **Determinism**: fixed tick (4 ticks = 1 s), seeded world generation, ties broken by id; same seed + same scripts = same match.
- **Enemy AI**: scripted in Python using the same `RobotAPI`/`BaseAPI` as the player, with three styles (rusher, turtle, economist)
  and difficulty-scaled reaction, economy and aggression.

## Sandbox (what it is and is not)
Scripts are parsed with `ast`, validated (forbidden names/attributes, only `math`/`random`), rewritten so arithmetic is guarded
(`**`, `*`, `+`, `<<` on huge values), executed with restricted builtins, and traced with `sys.settrace` for: instruction (line)
budget, wall-clock budget and a sampled memory-growth check (tracemalloc). Exceeding a budget aborts that call only.
**Limits**: it is an in-process language sandbox, not an OS process boundary; the memory check is sampled, so a single huge
allocation inside one builtin call can exceed it briefly. Unsupported: imports other than math/random, file/network/threads,
async, `str.format`, reflection, dunder/frame attributes.

## Rendering performance features
Per-robot LOD (animation and shadow cost reduced with distance), manual frustum culling of animated robots, instanced trees/rocks,
pooled effects (shots, sparks, explosions), quality presets (low/medium/high: shadows, pixel ratio, scenery density), capped pixel
ratio, fog-of-war baked into terrain vertex colours. `CW.stats()` exposes fps, draw calls, triangles and culled counts
(Game > Tools > Render statistics).

## Testing status (honest)
- Python engine, sandbox, lessons: pytest suite run in CI on CPython 3.12.
- Renderer: tested headlessly with Chromium + software GL (screenshots, no WebGL errors). **Not** benchmarked on real phones, so no
  device FPS claims are made.
- Dart UI: verified by `flutter analyze` and widget tests in CI plus a successful release build. The UI has not been exercised
  by hand on a physical device by the author.
- Game balance is only roughly tested (starter scripts, one map); Hard/Expert AI is weaker than a strong human player's scripts.

## Known limitations
- All robot classes use one base GLB model (RobotExpressive) with per-class accessories, colours and scale.
- arm64-v8a only. Test signing only; not Play Store ready.
- Game progress, scripts and saves use local storage; no cloud sync.
