from pathlib import Path

main = Path("app/src/main/java/com/chiyuri/player/MainActivity.kt")
s = main.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str) -> None:
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    s = s.replace(old, new, 1)

# Save fullscreen state across the Activity recreation caused by orientation changes.
replace_once(
    '    var isVideoFullscreen by remember { mutableStateOf(false) }\n',
    '    var isVideoFullscreen by rememberSaveable { mutableStateOf(false) }\n'
    '    var fullscreenVideoPortrait by rememberSaveable { mutableStateOf(false) }\n',
    "saveable fullscreen video orientation state"
)

# Playback in the app uses landscape by default for both audio and video.
# Fullscreen video allows an explicit portrait override, retained through rotation.
orientation_effect = '''    DisposableEffect(hostActivity, currentMediaUri, isVideoFullscreen, fullscreenVideoPortrait, playing) {
        val activity = hostActivity
        if (activity != null) {
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
        onDispose {
            activity?.requestedOrientation =
                android.content.pm.ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
    }

'''
replace_once(
    '    DisposableEffect(player) {\n',
    orientation_effect + '    DisposableEffect(player) {\n',
    "playback orientation controller"
)

# Add a rotation toggle beside the fullscreen exit control.
exit_button = '''            GothicIconButton(
                onClick = { isVideoFullscreen = false },
                modifier = Modifier.align(Alignment.TopEnd).padding(16.dp)
            ) {
                GothicIcon(Icons.Default.FullscreenExit, contentDescription = "Выйти из полноэкранного режима", tint = Color.White)
            }'''
rotate_button = '''            GothicIconButton(
                onClick = { fullscreenVideoPortrait = !fullscreenVideoPortrait },
                modifier = Modifier.align(Alignment.TopStart).padding(16.dp)
            ) {
                GothicIcon(
                    Icons.Default.ScreenRotation,
                    contentDescription = if (fullscreenVideoPortrait) "Повернуть видео в альбомную ориентацию" else "Повернуть видео в портретную ориентацию",
                    tint = Color.White
                )
            }
            GothicIconButton(
                onClick = { isVideoFullscreen = false },
                modifier = Modifier.align(Alignment.TopEnd).padding(16.dp)
            ) {
                GothicIcon(Icons.Default.FullscreenExit, contentDescription = "Выйти из полноэкранного режима", tint = Color.White)
            }'''
replace_once(exit_button, rotate_button, "fullscreen rotation button")

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

# Verify orientation handling is present exactly where expected.
for marker in [
    "SCREEN_ORIENTATION_LANDSCAPE",
    "SCREEN_ORIENTATION_PORTRAIT",
    "SCREEN_ORIENTATION_UNSPECIFIED",
    "Icons.Default.ScreenRotation",
    "rememberSaveable { mutableStateOf(false) }",
]:
    if marker not in s:
        raise SystemExit("Missing orientation implementation marker: " + marker)

print("PATCH_0431_OK: audio/video playback defaults to landscape; fullscreen video has a persistent portrait/landscape toggle; orientation resets on playback exit; v0.5.5 (341).")
