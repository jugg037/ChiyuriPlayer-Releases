from pathlib import Path
ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

(PKG / "VideoGestureMath.kt").write_text('''package com.chiyuri.player

import kotlin.math.roundToLong

internal fun videoSwipeSeekPosition(
    startPositionMs: Long,
    distancePx: Float,
    viewWidthPx: Int,
    durationMs: Long
): Long {
    if (viewWidthPx <= 0 || !distancePx.isFinite()) return startPositionMs.coerceAtLeast(0L)
    val delta = (distancePx / viewWidthPx.toFloat() * 60_000f).roundToLong()
    val maxPosition = durationMs.takeIf { it > 0L } ?: Long.MAX_VALUE
    return (startPositionMs + delta).coerceIn(0L, maxPosition)
}

internal fun videoSwipeLevel(startLevel: Int, distanceYpx: Float, viewHeightPx: Int, maxLevel: Int): Int {
    if (viewHeightPx <= 0 || maxLevel <= 0 || !distanceYpx.isFinite()) return startLevel.coerceIn(0, maxLevel.coerceAtLeast(0))
    val change = (distanceYpx / viewHeightPx.toFloat() * maxLevel).roundToLong().toInt()
    return (startLevel - change).coerceIn(0, maxLevel)
}
''', encoding="utf-8")

p = PKG / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
for import_line in [
    "import android.view.MotionEvent",
    "import android.view.ViewConfiguration",
    "import androidx.media3.ui.AspectRatioFrameLayout",
    "import kotlin.math.abs"
]:
    if import_line not in s:
        s = s.replace("import android.view.KeyEvent\n", "import android.view.KeyEvent\n" + import_line + "\n", 1)

s = s.replace('''    var fullscreenVideoPortrait by rememberSaveable { mutableStateOf(false) }
    val hostActivity''', '''    var fullscreenVideoPortrait by rememberSaveable { mutableStateOf(false) }
    var videoResizeMode by rememberSaveable { mutableIntStateOf(AspectRatioFrameLayout.RESIZE_MODE_FIT) }
    val hostActivity''', 1)
s = s.replace('''            useController = true
            setShowBuffering(PlayerView.SHOW_BUFFERING_NEVER)''', '''            useController = true
            resizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT
            setShowBuffering(PlayerView.SHOW_BUFFERING_NEVER)''', 1)

anchor = '''    BackHandler(enabled = isVideoFullscreen) {
        isVideoFullscreen = false
    }

    LaunchedEffect(hostActivity, currentMediaUri, isVideoFullscreen, fullscreenVideoPortrait, playing) {'''
replacement = '''    BackHandler(enabled = isVideoFullscreen) {
        isVideoFullscreen = false
    }

    LaunchedEffect(videoPlayerView, videoResizeMode) {
        videoPlayerView.resizeMode = videoResizeMode
    }

    DisposableEffect(videoPlayerView, isVideoFullscreen, hostActivity, player) {
        val activity = hostActivity
        if (!isVideoFullscreen || activity == null) {
            videoPlayerView.setOnTouchListener(null)
            onDispose { videoPlayerView.setOnTouchListener(null) }
        } else {
            val window = activity.window
            val originalBrightness = window.attributes.screenBrightness
            val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val touchSlop = ViewConfiguration.get(context).scaledTouchSlop
            var startX = 0f
            var startY = 0f
            var startPosition = 0L
            var startVolume = 0
            var startBrightness = 0.5f
            var gestureMode = 0
            videoPlayerView.setOnTouchListener { view, event ->
                when (event.actionMasked) {
                    MotionEvent.ACTION_DOWN -> {
                        startX = event.x
                        startY = event.y
                        startPosition = player.currentPosition.coerceAtLeast(0L)
                        startVolume = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC)
                        val brightness = window.attributes.screenBrightness
                        startBrightness = if (brightness in 0f..1f) brightness else 0.5f
                        gestureMode = 0
                        false
                    }
                    MotionEvent.ACTION_MOVE -> {
                        val dx = event.x - startX
                        val dy = event.y - startY
                        if (gestureMode == 0 && (abs(dx) > touchSlop || abs(dy) > touchSlop)) {
                            gestureMode = if (abs(dx) >= abs(dy)) 1 else if (startX < view.width / 2f) 2 else 3
                        }
                        when (gestureMode) {
                            1 -> player.seekTo(videoSwipeSeekPosition(startPosition, dx, view.width, player.duration))
                            2 -> {
                                val level = (startBrightness * 1000f).toInt().coerceIn(0, 1000)
                                val adjusted = videoSwipeLevel(level, dy, view.height, 1000) / 1000f
                                window.attributes = window.attributes.apply { screenBrightness = adjusted.coerceIn(0.05f, 1f) }
                            }
                            3 -> {
                                val maximum = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC).coerceAtLeast(1)
                                val adjusted = videoSwipeLevel(startVolume, dy, view.height, maximum)
                                audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, adjusted, 0)
                            }
                        }
                        gestureMode != 0
                    }
                    MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                        val completedMode = gestureMode
                        gestureMode = 0
                        if (completedMode != 0) {
                            val message = when (completedMode) {
                                1 -> "Перемотка: " + formatPlaybackTime(player.currentPosition)
                                2 -> "Яркость: " + ((window.attributes.screenBrightness.coerceIn(0.05f, 1f)) * 100).toInt() + "%"
                                else -> "Громкость: " + audioManager.getStreamVolume(AudioManager.STREAM_MUSIC) + "/" + audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                            }
                            android.widget.Toast.makeText(context, message, android.widget.Toast.LENGTH_SHORT).show()
                        }
                        completedMode != 0
                    }
                    else -> gestureMode != 0
                }
            }
            onDispose {
                videoPlayerView.setOnTouchListener(null)
                window.attributes = window.attributes.apply { screenBrightness = originalBrightness }
            }
        }
    }

    LaunchedEffect(hostActivity, currentMediaUri, isVideoFullscreen, fullscreenVideoPortrait, playing) {'''
if anchor not in s: raise SystemExit("patch_0439: fullscreen effect insertion anchor missing")
s = s.replace(anchor, replacement, 1)

rotation_block = '''            GothicIconButton(
                onClick = { fullscreenVideoPortrait = !fullscreenVideoPortrait },
                modifier = Modifier.align(Alignment.TopStart).padding(16.dp)
            ) {
                GothicIcon(
                    Icons.Default.ScreenRotation,
                    contentDescription = if (fullscreenVideoPortrait) "Включить автоматическую ориентацию" else "Зафиксировать портретную ориентацию",
                    tint = Color.White
                )
            }
'''
if rotation_block not in s: raise SystemExit("patch_0439: fullscreen rotation button block missing")
extra = rotation_block + '''            GothicIconButton(
                onClick = {
                    videoResizeMode = when (videoResizeMode) {
                        AspectRatioFrameLayout.RESIZE_MODE_FIT -> AspectRatioFrameLayout.RESIZE_MODE_FILL
                        AspectRatioFrameLayout.RESIZE_MODE_FILL -> AspectRatioFrameLayout.RESIZE_MODE_ZOOM
                        else -> AspectRatioFrameLayout.RESIZE_MODE_FIT
                    }
                },
                modifier = Modifier.align(Alignment.TopCenter).padding(16.dp)
            ) {
                GothicIcon(Icons.Default.AspectRatio, contentDescription = when (videoResizeMode) {
                    AspectRatioFrameLayout.RESIZE_MODE_FIT -> "Вписать видео"
                    AspectRatioFrameLayout.RESIZE_MODE_FILL -> "Растянуть видео"
                    else -> "Заполнить экран с обрезкой"
                }, tint = Color.White)
            }
            Row(
                modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 22.dp)
                    .background(Color.Black.copy(alpha = 0.55f), RoundedCornerShape(24.dp)),
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextButton(onClick = { player.seekTo((player.currentPosition - 1_000L).coerceAtLeast(0L)) }) {
                    Text("−1 с", color = Color.White)
                }
                TextButton(onClick = { player.seekTo((player.currentPosition + 1_000L).coerceAtMost(player.duration.takeIf { it > 0L } ?: Long.MAX_VALUE)) }) {
                    Text("+1 с", color = Color.White)
                }
            }
'''
s = s.replace(rotation_block, extra, 1)
p.write_text(s, encoding="utf-8")

(TEST / "VideoGestureMathTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Test

class VideoGestureMathTest {
    @Test fun horizontalSwipeSeeksProportionallyAndClamps() {
        assertEquals(60_000L, videoSwipeSeekPosition(30_000L, 500f, 500, 300_000L))
        assertEquals(0L, videoSwipeSeekPosition(500L, -500f, 500, 300_000L))
        assertEquals(300_000L, videoSwipeSeekPosition(290_000L, 500f, 500, 300_000L))
    }

    @Test fun verticalSwipeAdjustsLevelAndClamps() {
        assertEquals(75, videoSwipeLevel(50, -50f, 100, 100))
        assertEquals(25, videoSwipeLevel(50, 25f, 100, 100))
        assertEquals(100, videoSwipeLevel(95, -50f, 100, 100))
        assertEquals(0, videoSwipeLevel(5, 50f, 100, 100))
    }

    @Test fun invalidDimensionsLeaveCurrentValueUnchanged() {
        assertEquals(12L, videoSwipeSeekPosition(12L, 50f, 0, 1000L))
        assertEquals(12, videoSwipeLevel(12, 50f, 0, 100))
    }
}
''', encoding="utf-8")

print("patch_0439: fullscreen video fit/fill/zoom, seek steps, brightness/volume/seek gestures applied")
