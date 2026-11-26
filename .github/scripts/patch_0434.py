from pathlib import Path

main = Path("app/src/main/java/com/chiyuri/player/MainActivity.kt")
s = main.read_text(encoding="utf-8")

old_orientation = """            mediaPlaybackActive ->
                android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
"""
new_orientation = """            mediaPlaybackActive ->
                android.content.pm.ActivityInfo.SCREEN_ORIENTATION_FULL_SENSOR
"""
if s.count(old_orientation) != 1:
    raise SystemExit(f"automatic sensor orientation anchor mismatch: {s.count(old_orientation)}")
s = s.replace(old_orientation, new_orientation, 1)

old_label = 'contentDescription = if (fullscreenVideoPortrait) "Повернуть видео в альбомную ориентацию" else "Повернуть видео в портретную ориентацию"'
new_label = 'contentDescription = if (fullscreenVideoPortrait) "Включить автоматическую ориентацию" else "Зафиксировать портретную ориентацию"'
if s.count(old_label) != 1:
    raise SystemExit(f"fullscreen rotation label anchor mismatch: {s.count(old_label)}")
s = s.replace(old_label, new_label, 1)

main.write_text(s, encoding="utf-8")

gradle = Path("app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
if 'versionName = "0.5.5"' not in g or 'orElse("341")' not in g:
    raise SystemExit("Expected source baseline version 0.5.5 (341)")
g = g.replace('versionName = "0.5.5"', 'versionName = "0.5.6"', 1)
g = g.replace('orElse("341")', 'orElse("342")', 1)
gradle.write_text(g, encoding="utf-8")

for marker in [
    "SCREEN_ORIENTATION_FULL_SENSOR",
    "SCREEN_ORIENTATION_PORTRAIT",
    "SCREEN_ORIENTATION_UNSPECIFIED",
    "Включить автоматическую ориентацию",
    "fullscreenVideoPortrait = !fullscreenVideoPortrait",
]:
    if marker not in s:
        raise SystemExit("Missing sensor orientation marker: " + marker)
if "mediaPlaybackActive ->\n                android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE" in s:
    raise SystemExit("Forced landscape orientation is still present")

print("PATCH_0434_OK: playback follows all device sensor orientations; fullscreen video can temporarily lock portrait and return to sensor mode; v0.5.6 (342).")
