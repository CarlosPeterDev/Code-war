# Code Wars

An Android game where you **write real Python** to command a robot army. Mine ore, build robots, research upgrades and
destroy the enemy HQ on a 3D battlefield. Everything runs offline on the device.

- Flutter (Material 3, dark) UI, landscape gameplay
- Real 3D engine: three.js (WebGL) in a WebView, GLB robot model, lights, shadows, perspective camera, animations
- Real Python: CPython 3.12 embedded with Chaquopy, sandboxed (AST validation, restricted builtins, line/time/memory budgets)
- Modes: Campaign (13 missions), Robot Wars, Base Commander, Exploration, Factory Automation, Robot Racing, Sandbox, Quick Missions
- 5 difficulties, 5 worlds, 7 robot classes, enemy AI that uses the same API as you, post-match analysis
- Python editor: syntax highlighting, auto-indent, autocomplete, API help, error underlines, line numbers, breakpoints, undo/redo,
  search/replace, multiple files, templates, run/stop/reset test arena, console, variable inspection, execution history
- Learning Center: 15 interactive lessons, 11 programming puzzles, searchable API reference (93 documented entries)

## Download

Every push to `main` builds and publishes a release with separate assets: `code-wars-vX.Y.Z.apk`, `code-wars-vX.Y.Z.aab`
and `SHA256SUMS` (see the **Latest** release). Install the APK on an arm64 Android 7.0+ phone (allow "install unknown apps").
Builds are signed with the Flutter debug/test key: fine for testing, **not** production-signed and **not** Play Store ready.

## Repository layout

| Path | Purpose |
|---|---|
| `lib/` | Flutter UI (screens, editor, game screen, engine bridge, local storage) |
| `python/codewars/` | Game engine: simulation, sandbox, API, AI, modes, lessons, puzzles, analysis |
| `tests_py/` | pytest suite for engine, sandbox, lessons (run on CPython 3.12 in CI) |
| `renderer/` | three.js renderer source; `node build.mjs` bundles to `assets/renderer/index.html` |
| `android_overlay/`, `tool/patch_android.py` | Kotlin bridge + patching of the generated Android project (Chaquopy, arm64, manifest) |
| `.github/workflows/android-release.yml` | CI: Python tests, analyze, Flutter tests, APK + AAB, checksums, release |

See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions and limitations and [ASSET_LICENSES.md](ASSET_LICENSES.md) for credits.

## Local development

```
python -m pip install pytest && python -m pytest tests_py -q     # engine tests
cd renderer && npm ci && node build.mjs                          # rebuild the 3D bundle
flutter create --platforms=android --org com.codewars --project-name code_wars . && python3 tool/patch_android.py
flutter run
```
