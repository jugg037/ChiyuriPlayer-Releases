from pathlib import Path

base = Path("app/src/main/java/com/chiyuri/player")
main = base / "MainActivity.kt"
source = main.read_text(encoding="utf-8")

old = 'androidx.compose.ui.res.painterResource(com.chiyuri.player.R.mipmap.ic_launcher)'
new = 'androidx.compose.ui.res.painterResource(com.chiyuri.player.R.drawable.chiyuri_launcher_foreground)'
count = source.count(old)
if count != 1:
    raise SystemExit(f"Expected one Compose adaptive-icon reference, found {count}")
source = source.replace(old, new, 1)
main.write_text(source, encoding="utf-8")

gradle = Path("app/build.gradle.kts")
build = gradle.read_text(encoding="utf-8")
old_name = 'versionName = "0.5.1"'
if build.count(old_name) != 1:
    raise SystemExit("Expected exactly one versionName 0.5.1")
build = build.replace(old_name, 'versionName = "0.5.2"', 1)
old_code = 'versionCode = providers.gradleProperty("VERSION_CODE").orElse("337").get().toInt()'
if build.count(old_code) != 1:
    raise SystemExit("Expected exactly one versionCode fallback 337")
build = build.replace(old_code, 'versionCode = providers.gradleProperty("VERSION_CODE").orElse("338").get().toInt()', 1)
gradle.write_text(build, encoding="utf-8")

print("PATCH_0427_OK: Compose uses raster foreground resource; version 0.5.2 (338)")
