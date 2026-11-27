from pathlib import Path
ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

p = PKG / "PlaybackService.kt"
s = p.read_text(encoding="utf-8")
for import_line in [
    "import android.media.AudioDeviceCallback",
    "import android.media.AudioDeviceInfo",
    "import android.media.AudioManager",
    "import androidx.media3.common.AudioAttributes"
]:
    if import_line not in s:
        s = s.replace("import android.os.Handler\n", "import android.os.Handler\n" + import_line + "\n", 1)
s = s.replace('''    private var audioEffectsController: AudioEffectsController? = null
    private val progressHandler''', '''    private var audioEffectsController: AudioEffectsController? = null
    private var audioDeviceCallback: AudioDeviceCallback? = null
    private var pausedByOutputLoss = false
    private val progressHandler''', 1)
s = s.replace('''        val player = ExoPlayer.Builder(this).build()
        audioEffectsController''', '''        val player = ExoPlayer.Builder(this).build()
        player.setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(androidx.media3.common.C.USAGE_MEDIA)
                .setContentType(androidx.media3.common.C.AUDIO_CONTENT_TYPE_MUSIC)
                .build(),
            true
        )
        player.setHandleAudioBecomingNoisy(true)
        audioEffectsController''', 1)
s = s.replace('''            override fun onIsPlayingChanged(isPlaying: Boolean) {
                PlaybackQueueStore.save(this@PlaybackService, player)
            }

            override fun onPlaybackStateChanged''', '''            override fun onIsPlayingChanged(isPlaying: Boolean) {
                PlaybackQueueStore.save(this@PlaybackService, player)
            }

            override fun onPlayWhenReadyChanged(playWhenReady: Boolean, reason: Int) {
                if (playWhenReady) {
                    pausedByOutputLoss = false
                } else {
                    pausedByOutputLoss = reason == Player.PLAY_WHEN_READY_CHANGE_REASON_AUDIO_BECOMING_NOISY
                }
            }

            override fun onPlaybackStateChanged''', 1)
anchor = '''        mediaSession = MediaSession.Builder(this, player).build()
        progressHandler.postDelayed(progressSaver, SAVE_INTERVAL_MS)'''
replacement = '''        mediaSession = MediaSession.Builder(this, player).build()
        val audioManager = getSystemService(AUDIO_SERVICE) as AudioManager
        val deviceCallback = object : AudioDeviceCallback() {
            override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>) {
                val headsetReconnected = addedDevices.any { isHeadsetOutputDevice(it.type) }
                if (shouldResumeAfterHeadsetReconnect(pausedByOutputLoss, headsetReconnected, player.playbackState != Player.STATE_IDLE)) {
                    progressHandler.postDelayed({
                        if (pausedByOutputLoss && !player.playWhenReady && player.playbackState != Player.STATE_IDLE) {
                            pausedByOutputLoss = false
                            player.play()
                        }
                    }, OUTPUT_RECONNECT_RESUME_DELAY_MS)
                }
            }
        }
        audioDeviceCallback = deviceCallback
        audioManager.registerAudioDeviceCallback(deviceCallback, progressHandler)
        progressHandler.postDelayed(progressSaver, SAVE_INTERVAL_MS)'''
if anchor not in s: raise SystemExit("patch_0440: media session registration anchor missing")
s = s.replace(anchor, replacement, 1)
s = s.replace('''    override fun onDestroy() {
        progressHandler.removeCallbacks(progressSaver)
        AudioVisualizerBridge.unbind()''', '''    override fun onDestroy() {
        progressHandler.removeCallbacks(progressSaver)
        audioDeviceCallback?.let { callback ->
            (getSystemService(AUDIO_SERVICE) as AudioManager).unregisterAudioDeviceCallback(callback)
        }
        audioDeviceCallback = null
        AudioVisualizerBridge.unbind()''', 1)
s = s.replace('''    private companion object {
        const val SAVE_INTERVAL_MS = 5_000L
    }
}''', '''    private companion object {
        const val SAVE_INTERVAL_MS = 5_000L
        const val OUTPUT_RECONNECT_RESUME_DELAY_MS = 900L
    }
}

internal fun isHeadsetOutputDevice(type: Int): Boolean = type in setOf(
    AudioDeviceInfo.TYPE_WIRED_HEADSET,
    AudioDeviceInfo.TYPE_WIRED_HEADPHONES,
    AudioDeviceInfo.TYPE_BLUETOOTH_A2DP,
    AudioDeviceInfo.TYPE_BLUETOOTH_SCO,
    AudioDeviceInfo.TYPE_USB_HEADSET
)

internal fun shouldResumeAfterHeadsetReconnect(
    pausedByOutputLoss: Boolean,
    headsetReconnected: Boolean,
    playerReady: Boolean
): Boolean = pausedByOutputLoss && headsetReconnected && playerReady
''', 1)
p.write_text(s, encoding="utf-8")

(TEST / "PlaybackOutputReconnectTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PlaybackOutputReconnectTest {
    @Test fun resumesOnlyAfterNoisePauseAndHeadsetReconnect() {
        assertTrue(shouldResumeAfterHeadsetReconnect(true, true, true))
        assertFalse(shouldResumeAfterHeadsetReconnect(false, true, true))
        assertFalse(shouldResumeAfterHeadsetReconnect(true, false, true))
        assertFalse(shouldResumeAfterHeadsetReconnect(true, true, false))
    }
}
''', encoding="utf-8")

print("patch_0440: explicit audio focus/noisy handling and guarded headset reconnect resume applied")
