from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0458: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")
TEST = Path("app/src/test/java/com/chiyuri/player")

p = PKG / "PlaybackPreferencesStore.kt"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "    val gaplessPlayback: Boolean = true\n)",
    "    val gaplessPlayback: Boolean = true,\n    val transitionFadeMs: Int = 0\n)",
    1
)
s = s.replace(
    '    internal const val KEY_GAPLESS = "gapless_playback"',
    '    internal const val KEY_GAPLESS = "gapless_playback"\n    internal const val KEY_TRANSITION_FADE = "transition_fade_ms"',
    1
)
s = s.replace(
    "        return PlaybackPreferences(gaplessPlayback = prefs.getBoolean(KEY_GAPLESS, true))",
    "        return PlaybackPreferences(\n            gaplessPlayback = prefs.getBoolean(KEY_GAPLESS, true),\n            transitionFadeMs = prefs.getInt(KEY_TRANSITION_FADE, 0).coerceIn(0, 8000)\n        )",
    1
)
s = s.replace(
    "            putBoolean(KEY_GAPLESS, preferences.gaplessPlayback)",
    "            putBoolean(KEY_GAPLESS, preferences.gaplessPlayback)\n            putInt(KEY_TRANSITION_FADE, preferences.transitionFadeMs.coerceIn(0, 8000))",
    1
)
p.write_text(s, encoding="utf-8")

p = PKG / "AudioEffectsController.kt"
s = p.read_text(encoding="utf-8")
s = s.replace("    private var replayGainDb: Float = 0f", "    private var replayGainDb: Float = 0f\n    private var transitionGain: Float = 1f", 1)
s = s.replace(
    '''    fun setReplayGainDb(gainDb: Float?) {
        replayGainDb = gainDb?.takeIf { it.isFinite() }?.coerceIn(-12f, 12f) ?: 0f
        applySettings()
    }''',
    '''    fun setReplayGainDb(gainDb: Float?) {
        replayGainDb = gainDb?.takeIf { it.isFinite() }?.coerceIn(-12f, 12f) ?: 0f
        applySettings()
    }

    fun setTransitionGain(gain: Float) {
        val normalized = gain.takeIf { it.isFinite() }?.coerceIn(0f, 1f) ?: 1f
        if (kotlin.math.abs(normalized - transitionGain) < 0.01f) return
        transitionGain = normalized
        applyPlayerVolume(AudioEffectsSettings.load(appContext))
    }''',
    1
)
s = s.replace(
    '''        player.volume = if (activeReplayGain < 0f) 10.0.pow(activeReplayGain.toDouble() / 20.0).toFloat().coerceIn(0.1f, 1f) else 1f
        loudnessEnhancer?.let { effect ->''',
    '''        applyPlayerVolume(config)
        loudnessEnhancer?.let { effect ->''',
    1
)
anchor = '''    private fun releaseEffects() {'''
helper = '''    private fun applyPlayerVolume(config: AudioEffectsConfig) {
        val activeReplayGain = if (config.replayGainEnabled) replayGainDb else 0f
        val replayGainAttenuation = if (activeReplayGain < 0f) {
            10.0.pow(activeReplayGain.toDouble() / 20.0).toFloat().coerceIn(0.1f, 1f)
        } else 1f
        player.volume = (replayGainAttenuation * transitionGain).coerceIn(0f, 1f)
    }

'''
if anchor not in s: raise SystemExit("patch_0458: audio volume helper anchor missing")
s = s.replace(anchor, helper + anchor, 1)
p.write_text(s, encoding="utf-8")

# A single-player fade transition is intentionally sequential, not overlapping audio.
p = PKG / "PlaybackService.kt"
s = p.read_text(encoding="utf-8")
if "import android.os.SystemClock" not in s:
    s = s.replace("import android.os.Looper", "import android.os.Looper\nimport android.os.SystemClock", 1)
s = s.replace(
    "    private var replayGainJob: Job? = null",
    "    private var replayGainJob: Job? = null\n    private var transitionFadingOut = false\n    private var transitionFadeInStartedAtMs = -1L",
    1
)
anchor = '''    override fun onCreate() {'''
monitor = '''    private val transitionMonitor = object : Runnable {
        override fun run() {
            val player = mediaSession?.player
            val fadeDurationMs = PlaybackPreferencesStore.load(this@PlaybackService).transitionFadeMs.toLong()
            if (player == null || fadeDurationMs <= 0L) {
                transitionFadingOut = false
                transitionFadeInStartedAtMs = -1L
                audioEffectsController?.setTransitionGain(1f)
            } else if (transitionFadeInStartedAtMs >= 0L) {
                val elapsed = (SystemClock.elapsedRealtime() - transitionFadeInStartedAtMs).coerceAtLeast(0L)
                val gain = calculateFadeInGain(elapsed, fadeDurationMs)
                audioEffectsController?.setTransitionGain(gain)
                if (gain >= 1f) transitionFadeInStartedAtMs = -1L
            } else if (player.isPlaying && player.duration > 0L && player.hasNextMediaItem()) {
                val remaining = (player.duration - player.currentPosition).coerceAtLeast(0L)
                if (remaining <= fadeDurationMs) {
                    transitionFadingOut = true
                    audioEffectsController?.setTransitionGain(calculateFadeOutGain(remaining, fadeDurationMs))
                } else if (!transitionFadingOut) {
                    audioEffectsController?.setTransitionGain(1f)
                }
            } else if (!transitionFadingOut) {
                audioEffectsController?.setTransitionGain(1f)
            }
            progressHandler.postDelayed(this, 100L)
        }
    }

'''
if anchor not in s: raise SystemExit("patch_0458: service onCreate anchor missing")
s = s.replace(anchor, monitor + anchor, 1)

s = s.replace(
    '''                PlaybackWidgetProvider.updateAll(this@PlaybackService, player)
                applyReplayGainFor(player, mediaItem)
            }

            override fun onIsPlayingChanged(isPlaying: Boolean) {
                PlaybackQueueStore.save(this@PlaybackService, player)''',
    '''                PlaybackWidgetProvider.updateAll(this@PlaybackService, player)
                applyReplayGainFor(player, mediaItem)
                if (transitionFadingOut || reason == Player.MEDIA_ITEM_TRANSITION_REASON_AUTO) {
                    transitionFadingOut = false
                    transitionFadeInStartedAtMs = SystemClock.elapsedRealtime()
                }
            }

            override fun onIsPlayingChanged(isPlaying: Boolean) {
                if (!isPlaying && !player.playWhenReady) {
                    transitionFadingOut = false
                    transitionFadeInStartedAtMs = -1L
                    audioEffectsController?.setTransitionGain(1f)
                }
                PlaybackQueueStore.save(this@PlaybackService, player)''',
    1
)
s = s.replace(
    '''                if (playbackState == Player.STATE_ENDED || playbackState == Player.STATE_IDLE) {
                    PlaybackQueueStore.save(this@PlaybackService, player)
                }''',
    '''                if (playbackState == Player.STATE_ENDED || playbackState == Player.STATE_IDLE) {
                    transitionFadingOut = false
                    transitionFadeInStartedAtMs = -1L
                    audioEffectsController?.setTransitionGain(1f)
                    PlaybackQueueStore.save(this@PlaybackService, player)
                }''',
    1
)
s = s.replace(
    "        mediaSession = MediaLibrarySession.Builder(this, player, LibraryCallback()).build()",
    "        mediaSession = MediaLibrarySession.Builder(this, player, LibraryCallback()).build()\n        progressHandler.postDelayed(transitionMonitor, 100L)",
    1
)
s = s.replace(
    "        progressHandler.removeCallbacks(progressSaver)",
    "        progressHandler.removeCallbacks(progressSaver)\n        progressHandler.removeCallbacks(transitionMonitor)",
    1
)
s += '''

internal fun calculateFadeOutGain(remainingMs: Long, durationMs: Long): Float {
    if (durationMs <= 0L) return 1f
    return (remainingMs.toFloat() / durationMs.toFloat()).coerceIn(0f, 1f)
}

internal fun calculateFadeInGain(elapsedMs: Long, durationMs: Long): Float {
    if (durationMs <= 0L) return 1f
    return (elapsedMs.toFloat() / durationMs.toFloat()).coerceIn(0f, 1f)
}
'''
p.write_text(s, encoding="utf-8")

# Persist the transition setting in backups while remaining compatible with older archives.
p = PKG / "LibraryBackupManager.kt"
s = p.read_text(encoding="utf-8")
s = s.replace(
    'PlaybackPreferences(gaplessPlayback = playbackPreferencesObject.optBoolean("gapless_playback", true))',
    'PlaybackPreferences(\n                    gaplessPlayback = playbackPreferencesObject.optBoolean("gapless_playback", true),\n                    transitionFadeMs = playbackPreferencesObject.optInt("transition_fade_ms", 0).coerceIn(0, 8000)\n                )',
    1
)
s = s.replace(
    '.put("gapless_playback", PlaybackPreferencesStore.load(context).gaplessPlayback)',
    '.put("gapless_playback", PlaybackPreferencesStore.load(context).gaplessPlayback)\n            .put("transition_fade_ms", PlaybackPreferencesStore.load(context).transitionFadeMs)',
    1
)
p.write_text(s, encoding="utf-8")

# Add an explicit user control; zero seconds disables the effect.
p = PKG / "PartyModeScreen.kt"
s = p.read_text(encoding="utf-8")
if "import androidx.compose.material3.Slider" not in s:
    s = s.replace("import androidx.compose.material3.Switch", "import androidx.compose.material3.Switch\nimport androidx.compose.material3.Slider", 1)
replace_once(
    p,
    '''                )
            }
        }
    }
}

@Composable
internal fun PartyModeScreen''',
    '''                )
            }
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Плавный переход", color = MaterialTheme.colorScheme.onSurface)
                    Text(
                        if (preferences.transitionFadeMs == 0) "Выкл." else "${preferences.transitionFadeMs / 1000f} с",
                        color = MaterialTheme.colorScheme.primary
                    )
                }
                Text(
                    "Затухание в конце и нарастание в начале следующей композиции. Дорожки не накладываются друг на друга.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Slider(
                    value = preferences.transitionFadeMs.toFloat(),
                    onValueChange = { value ->
                        preferences = preferences.copy(transitionFadeMs = value.toInt().coerceIn(0, 8000))
                        PlaybackPreferencesStore.save(context, preferences)
                    },
                    valueRange = 0f..8000f,
                    steps = 7
                )
            }
        }
    }
}

@Composable
internal fun PartyModeScreen''',
    "transition fade slider"
)
p.write_text(s, encoding="utf-8")

(TEST / "PlaybackPreferencesTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Test

class PlaybackPreferencesTest {
    @Test fun fadeOutGainFallsAsTheCurrentTrackEnds() {
        assertEquals(1f, calculateFadeOutGain(8000L, 4000L), 0.001f)
        assertEquals(0.5f, calculateFadeOutGain(2000L, 4000L), 0.001f)
        assertEquals(0f, calculateFadeOutGain(0L, 4000L), 0.001f)
    }

    @Test fun fadeInGainRisesFromSilenceAndClamps() {
        assertEquals(0f, calculateFadeInGain(0L, 4000L), 0.001f)
        assertEquals(0.5f, calculateFadeInGain(2000L, 4000L), 0.001f)
        assertEquals(1f, calculateFadeInGain(8000L, 4000L), 0.001f)
        assertEquals(1f, calculateFadeInGain(100L, 0L), 0.001f)
    }
}
''', encoding="utf-8")

print("patch_0458: configurable sequential fade-out/fade-in transition added with backup persistence and unit tests")
