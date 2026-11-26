from pathlib import Path

main = Path("app/src/main/java/com/chiyuri/player/MainActivity.kt")
s = main.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str) -> None:
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    s = s.replace(old, new, 1)

# Preserve fullscreen UI and the selected orientation across Android Activity recreation.
replace_once(
    '    var isVideoFullscreen by remember { mutableStateOf(false) }\n',
    '    var isVideoFullscreen by rememberSaveable { mutableStateOf(false) }\n'
    '    var fullscreenVideoPortrait by rememberSaveable { mutableStateOf(false) }\n',
    "saveable fullscreen orientation state"
)

# Update orientation when playback/fullscreen state changes. Keep cleanup in a
# separate Activity-keyed effect so changing orientation does not briefly reset
# to UNSPECIFIED and trigger a second, unnecessary configuration change.
orientation_effect = '''    LaunchedEffect(hostActivity, currentMediaUri, isVideoFullscreen, fullscreenVideoPortrait, playing) {
        val activity = hostActivity ?: return@LaunchedEffect
        val mediaPlaybackActive = currentMediaUri != null &&
            player.playbackState != Player.STATE_IDLE
        activity.requestedOrientation = when {
            mediaPlaybackActive && isVideoFullscreen && fullscreenVideoPortrait ->
                android.content.pm.ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
            mediaPlaybackActive ->
                android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
            else ->
                android.content.pm.ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
    }

    DisposableEffect(hostActivity) {
        onDispose {
            hostActivity?.requestedOrientation =
                android.content.pm.ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
    }

'''
replace_once(
    '    DisposableEffect(player) {\n',
    orientation_effect + '    DisposableEffect(player) {\n',
    "playback orientation controller"
)

# Add a portrait/landscape toggle immediately before the existing fullscreen exit button.
exit_icon = 'GothicIcon(Icons.Default.FullscreenExit, contentDescription = "Выйти из полноэкранного режима", tint = Color.White)'
if s.count(exit_icon) != 1:
    raise SystemExit(f"Fullscreen exit icon anchor mismatch: {s.count(exit_icon)}")
icon_pos = s.index(exit_icon)
button_pos = s.rfind("            GothicIconButton(", 0, icon_pos)
fullscreen_pos = s.rfind("    if (isVideoFullscreen)", 0, icon_pos)
if button_pos < fullscreen_pos or fullscreen_pos < 0:
    raise SystemExit("Could not locate fullscreen exit button inside fullscreen overlay")
rotation_button = '''            GothicIconButton(
                onClick = { fullscreenVideoPortrait = !fullscreenVideoPortrait },
                modifier = Modifier.align(Alignment.TopStart).padding(16.dp)
            ) {
                GothicIcon(
                    Icons.Default.ScreenRotation,
                    contentDescription = if (fullscreenVideoPortrait) "Повернуть видео в альбомную ориентацию" else "Повернуть видео в портретную ориентацию",
                    tint = Color.White
                )
            }
'''
s = s[:button_pos] + rotation_button + s[button_pos:]

if "import androidx.compose.runtime.LaunchedEffect" not in s:
    s = s.replace("import androidx.compose.runtime.DisposableEffect\n", "import androidx.compose.runtime.DisposableEffect\nimport androidx.compose.runtime.LaunchedEffect\n", 1)

main.write_text(s, encoding="utf-8")

gradle = Path("app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
if 'versionName = "0.5.4"' not in g:
    raise SystemExit("Expected source baseline versionName 0.5.4")
g = g.replace('versionName = "0.5.4"', 'versionName = "0.5.5"', 1)
if 'orElse("340")' not in g:
    raise SystemExit("Expected source baseline versionCode 340")
g = g.replace('orElse("340")', 'orElse("341")', 1)
gradle.write_text(g, encoding="utf-8")

for marker in [
    "SCREEN_ORIENTATION_LANDSCAPE",
    "SCREEN_ORIENTATION_PORTRAIT",
    "SCREEN_ORIENTATION_UNSPECIFIED",
    "Icons.Default.ScreenRotation",
    "rememberSaveable { mutableStateOf(false) }",
    "LaunchedEffect(hostActivity, currentMediaUri, isVideoFullscreen, fullscreenVideoPortrait, playing)",
]:
    if marker not in s:
        raise SystemExit("Missing orientation implementation marker: " + marker)

print("PATCH_0431_OK: audio/video playback defaults to landscape; fullscreen video has a portrait/landscape toggle; orientation cleanup is Activity-scoped; state survives rotation; v0.5.5 (341).")
