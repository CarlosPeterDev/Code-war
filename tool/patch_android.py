"""Apply Code Wars Android customisations on top of `flutter create` output."""
import pathlib, re, shutil

root = pathlib.Path("android")
ov = pathlib.Path("android_overlay")

# 1. Python sources + Kotlin activity
shutil.copytree(ov / "python", root / "app/src/main/python", dirs_exist_ok=True)
for p in (root / "app/src/main/kotlin").rglob("MainActivity.kt"):
    p.unlink()
dest = root / "app/src/main/kotlin/com/codewars/game"
dest.mkdir(parents=True, exist_ok=True)
shutil.copy(ov / "kotlin/MainActivity.kt", dest / "MainActivity.kt")

# 2. settings.gradle(.kts): declare Chaquopy plugin
for name in ("settings.gradle.kts", "settings.gradle"):
    f = root / name
    if f.exists():
        s = f.read_text()
        kts = name.endswith(".kts")
        line = ('    id("com.chaquo.python") version "17.0.0" apply false\n' if kts
                else '    id "com.chaquo.python" version "17.0.0" apply false\n')
        s = re.sub(r"(plugins\s*\{\n)(\s*id\(?\"dev\.flutter\.flutter-plugin-loader\")",
                   lambda m: m.group(1) + line + m.group(2), s, count=1)
        assert "com.chaquo.python" in s, "settings patch failed"
        f.write_text(s)

# 3. app build file
for name in ("build.gradle.kts", "build.gradle"):
    f = root / "app" / name
    if f.exists():
        s = f.read_text()
        kts = name.endswith(".kts")
        s = re.sub(r"(plugins\s*\{\n)",
                   lambda m: m.group(1) + ('    id("com.chaquo.python")\n' if kts else '    id "com.chaquo.python"\n'),
                   s, count=1)
        s = re.sub(r'namespace\s*=\s*"[^"]+"', 'namespace = "com.codewars.game"', s)
        s = re.sub(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "com.codewars.game"', s)
        s = re.sub(r"minSdk\s*=\s*\S+", "minSdk = 24", s)
        s = s.replace("ndk {", "ndk {")  # no-op marker
        s += '''
// Release-only game build: Chaquopy has no armeabi-v7a for Python 3.12 and the
// Flutter plugin adds it to the debug variant, so debug is disabled here.
androidComponents {
    beforeVariants(selector().withBuildType("debug")) { it.enable = false }
}

chaquopy {
    defaultConfig {
        version = "3.12"
    }
}
'''
        # ARM64 only
        s = re.sub(r"(defaultConfig\s*\{[ \t]*\n)",
                   lambda m: m.group(1) + ('        ndk { abiFilters += listOf("arm64-v8a") }\n' if kts else '        ndk { abiFilters "arm64-v8a" }\n'), s, count=1)
        assert "abiFilters" in s, "abiFilters patch failed"
        f.write_text(s)
        print(s)
print("patched")
