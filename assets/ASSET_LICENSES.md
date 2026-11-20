# Asset and third-party licenses

Every third-party asset used by Code Wars, with its source, creator, license and attribution requirements.
Only assets whose license permits this use and redistribution are included. Nothing else is bundled.

## 3D assets

| Asset | Source URL | Creator | License | Download date | Attribution |
|---|---|---|---|---|---|
| RobotExpressive.glb (robot model with 14 animations) | https://github.com/mrdoob/three.js/blob/dev/examples/models/gltf/RobotExpressive/RobotExpressive.glb (README: https://github.com/mrdoob/three.js/blob/dev/examples/models/gltf/RobotExpressive/README.md) | Tomas Laulhe (https://www.patreon.com/quaternius); modifications by Don McCurdy (morph targets, FBX2GLTF conversion, material cleanup) | CC0 1.0 Universal | 2026-11-19 | None required. Credit given here voluntarily; the creator asks users to consider supporting him on Patreon. |

The robot model is the only third-party 3D asset. Everything else visible in the 3D view is original and
generated at runtime by `renderer/src/main.js`:
- structures (HQ, turret, wall, solar panel, refinery, factory) are composed from procedural meshes,
- class accessories (backpacks, hard hat, shoulder plates, antenna, cannons, halo) are procedural meshes,
- ore crystals, trees and rocks are procedural/instanced meshes,
- terrain, ground, metal and solar-panel textures are generated on a canvas at load time.

Every robot class uses the single RobotExpressive base model plus original per-class accessories, scale and
colours. There are no per-class custom character models (see ARCHITECTURE.md, Known limitations).

## Software

| Component | Source | License |
|---|---|---|
| three.js 0.170.0 (bundled in `assets/renderer/index.html`, incl. OrbitControls, GLTFLoader, SkeletonUtils, RoomEnvironment) | https://github.com/mrdoob/three.js | MIT |
| Chaquopy 17.0.0 (embedded CPython 3.12 for Android) | https://chaquo.com/chaquopy/ | MIT (CPython: PSF License) |
| Flutter / Dart SDK | https://flutter.dev | BSD-3-Clause |
| webview_flutter | https://pub.dev/packages/webview_flutter | BSD-3-Clause |
| shared_preferences | https://pub.dev/packages/shared_preferences | BSD-3-Clause |
| esbuild 0.24.0 (build-time only) | https://github.com/evanw/esbuild | MIT |

Code Wars was inspired by the *ideas* of programming games such as Screeps, Gladiabots, Colobot and
CodeCombat. No code, graphics, names or assets from those games are used.
